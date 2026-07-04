"""
FastAPI 백엔드: 정적 Tailwind 프론트엔드(static/index.html)를 서빙하고,
/api/chat 에서 Naive RAG와 Advanced RAG(질의 확장) 답변을 동시에 생성해 비교용으로 반환한다.
서버 기동 시 documents/ 폴더 실시간 감시(watch_documents)도 함께 시작한다.
"""

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from rag_pipeline import compare_rag
from watch_documents import start_watcher

app = FastAPI(title="병무청 보도자료 Q&A")

_watcher = None


@app.on_event("startup")
def _on_startup():
    global _watcher
    _watcher = start_watcher()


@app.on_event("shutdown")
def _on_shutdown():
    if _watcher is not None:
        _watcher.stop()
        _watcher.join()


class ChatRequest(BaseModel):
    query: str


class Source(BaseModel):
    document_title: str | None = None
    press_date: str | None = None
    section_heading: str | None = None
    content: str


class RagResult(BaseModel):
    answer: str
    sources: list[Source]
    query_variants: list[str] | None = None


class ChatResponse(BaseModel):
    naive: RagResult
    advanced: RagResult


def _to_result(raw: dict) -> RagResult:
    sources = [
        Source(
            document_title=c["metadata"].get("document_title"),
            press_date=c["metadata"].get("press_date"),
            section_heading=c["metadata"].get("section_heading"),
            content=c["content"],
        )
        for c in raw["sources"]
    ]
    return RagResult(answer=raw["answer"], sources=sources, query_variants=raw.get("query_variants"))


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = compare_rag(req.query)
    return ChatResponse(naive=_to_result(result["naive"]), advanced=_to_result(result["advanced"]))


app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")
