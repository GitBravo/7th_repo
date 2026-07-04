"""
RAG 파이프라인 두 가지를 제공한다 (compare_rag로 동시 비교):

- Naive RAG (run_naive_rag): 원본 질문 그대로 벡터 검색(top-10) -> Cohere rerank(top-4) -> 답변 생성
- Advanced RAG (run_advanced_rag): 질의 확장(Multi-Query Expansion, LLM으로 원 질문의 다른 표현
  3개 생성) -> 원본+확장 질의 각각 벡터 검색 후 병합/중복제거 -> Cohere rerank(top-4) -> 답변 생성
  (질의 확장으로 검색 재현율(recall)을 높이는 것이 Naive RAG 대비 핵심 차이)

두 파이프라인 모두 rerank/생성 단계는 동일 로직을 공유하므로, 답변 품질 차이는
"검색 단계"(단일 질의 vs 다중 질의 확장)에서만 발생하도록 설계했다.
"""

import os

import cohere
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "openai/gpt-4o-mini"
RERANK_MODEL = "rerank-multilingual-v3.0"

VECTOR_TOP_K = 10
RERANK_TOP_N = 4
QUERY_VARIANT_COUNT = 3
MULTI_QUERY_TOP_K_EACH = 6

SYSTEM_PROMPT = (
    "당신은 병무청 보도자료 내용을 바탕으로 답변하는 어시스턴트입니다. "
    "아래 제공된 참고 자료(context)에 근거해서만 답변하고, "
    "참고 자료에서 확인할 수 없는 내용은 모른다고 답하세요. "
    "답변 마지막 줄에 참고한 보도자료 제목을 표기하세요."
)

_openai_client = OpenAI(api_key=OPENAI_API_KEY)
_openrouter_client = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")
_cohere_client = cohere.Client(COHERE_API_KEY) if COHERE_API_KEY else None
_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def embed_query(query: str):
    resp = _openai_client.embeddings.create(model=EMBED_MODEL, input=[query])
    return resp.data[0].embedding


def vector_search(query: str, top_k: int = VECTOR_TOP_K):
    query_embedding = embed_query(query)
    res = _supabase.rpc("match_news_chunks", {
        "query_embedding": query_embedding,
        "match_count": top_k,
        "filter": {},
    }).execute()
    return res.data


def rerank(query: str, candidates, top_n: int = RERANK_TOP_N):
    if not candidates:
        return []
    if _cohere_client is None:
        raise RuntimeError("COHERE_API_KEY가 .env에 설정되지 않았습니다.")
    documents = [c["content"] for c in candidates]
    result = _cohere_client.rerank(
        model=RERANK_MODEL,
        query=query,
        documents=documents,
        top_n=min(top_n, len(documents)),
    )
    return [candidates[r.index] for r in result.results]


def build_context(chunks):
    parts = []
    for c in chunks:
        md = c["metadata"]
        parts.append(f"[{md.get('document_title')} ({md.get('press_date')})]\n{c['content']}")
    return "\n\n---\n\n".join(parts)


def generate_answer(query: str, chunks):
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY가 .env에 설정되지 않았습니다.")
    context = build_context(chunks)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"참고 자료:\n{context}\n\n질문: {query}"},
    ]
    resp = _openrouter_client.chat.completions.create(model=CHAT_MODEL, messages=messages)
    return resp.choices[0].message.content


def generate_query_variants(query: str, n: int = QUERY_VARIANT_COUNT):
    """LLM으로 원 질문을 다른 키워드/관점의 검색 질의 n개로 확장 (Multi-Query Expansion)."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY가 .env에 설정되지 않았습니다.")
    prompt = (
        f"다음 사용자 질문의 검색 재현율을 높이기 위해, 서로 다른 키워드/관점을 사용한 "
        f"검색 질의 {n}개를 생성하세요. 각 질의는 원래 의도를 유지해야 합니다. "
        f"다른 설명이나 번호 없이 한 줄에 하나씩 질의만 출력하세요.\n\n질문: {query}"
    )
    resp = _openrouter_client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    lines = [
        line.strip(" -•·0123456789.\t")
        for line in resp.choices[0].message.content.strip().split("\n")
        if line.strip()
    ]
    return lines[:n]


def multi_query_vector_search(query: str, top_k_each: int = MULTI_QUERY_TOP_K_EACH):
    variants = generate_query_variants(query)
    all_queries = [query] + variants

    merged = {}
    for q in all_queries:
        for candidate in vector_search(q, top_k=top_k_each):
            cid = candidate["id"]
            if cid not in merged or candidate["similarity"] > merged[cid]["similarity"]:
                merged[cid] = candidate

    return list(merged.values()), variants


def run_naive_rag(query: str):
    candidates = vector_search(query, top_k=VECTOR_TOP_K)
    top_chunks = rerank(query, candidates, top_n=RERANK_TOP_N)
    answer = generate_answer(query, top_chunks)
    return {"answer": answer, "sources": top_chunks}


def run_advanced_rag(query: str):
    candidates, variants = multi_query_vector_search(query)
    top_chunks = rerank(query, candidates, top_n=RERANK_TOP_N)
    answer = generate_answer(query, top_chunks)
    return {"answer": answer, "sources": top_chunks, "query_variants": variants}


def compare_rag(query: str):
    return {
        "naive": run_naive_rag(query),
        "advanced": run_advanced_rag(query),
    }
