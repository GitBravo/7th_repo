"""
청크를 OpenAI로 임베딩하고 Supabase news_chunks 테이블에 적재하는 공용 로직.
embed_and_upload.py(배치)와 watch_documents.py(실시간) 양쪽에서 공유한다.

같은 source_file의 기존 청크는 재적재 전에 삭제하므로, 동일 문서를 다시
처리해도(재실행/재감지) 중복 행이 쌓이지 않는다 (idempotent).
"""

import os

from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

TABLE_NAME = "news_chunks"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
EMBED_BATCH = 100
INSERT_BATCH = 100

assert OPENAI_API_KEY and OPENAI_API_KEY.startswith("sk-"), "OPENAI_API_KEY를 .env에 설정하세요."
assert SUPABASE_URL and SUPABASE_URL.startswith("http"), "SUPABASE_URL을 .env에 설정하세요."
assert SUPABASE_KEY, "SUPABASE_KEY를 .env에 설정하세요."

_openai_client = OpenAI(api_key=OPENAI_API_KEY)
_supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def embed_texts(texts):
    embeddings = []
    for i in range(0, len(texts), EMBED_BATCH):
        batch = texts[i:i + EMBED_BATCH]
        resp = _openai_client.embeddings.create(model=EMBED_MODEL, input=batch)
        embeddings.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
    return embeddings


def delete_chunks_by_source(source_file):
    """같은 source_file의 기존 청크를 삭제 (재적재 시 중복 방지)."""
    _supabase.table(TABLE_NAME).delete().eq("metadata->>source_file", source_file).execute()


def insert_chunks(chunks, embeddings):
    rows = [
        {"content": c["content"], "embedding": emb, "metadata": c["metadata"]}
        for c, emb in zip(chunks, embeddings)
    ]
    for i in range(0, len(rows), INSERT_BATCH):
        _supabase.table(TABLE_NAME).insert(rows[i:i + INSERT_BATCH]).execute()
    return len(rows)


def embed_and_load_chunks(chunks, replace_existing=True):
    """청크 리스트를 임베딩 후 Supabase에 적재."""
    if not chunks:
        return 0

    if replace_existing:
        source_files = {c["metadata"]["source_file"] for c in chunks}
        for source_file in source_files:
            delete_chunks_by_source(source_file)

    embeddings = embed_texts([c["embed_text"] for c in chunks])
    assert len(embeddings) == len(chunks), "임베딩 개수 불일치"
    assert len(embeddings[0]) == EMBED_DIM, f"차원 불일치: {len(embeddings[0])}"

    return insert_chunks(chunks, embeddings)
