"""
chunks_news.json 을 읽어 OpenAI text-embedding-3-small 로 임베딩한 뒤
Supabase news_chunks 테이블에 적재한다 (일괄 재적재용).

사전 준비:
1. .env 에 SUPABASE_URL, SUPABASE_KEY(service_role), OPENAI_API_KEY 설정
2. sql/setup_supabase.sql 을 Supabase SQL Editor에서 실행해 news_chunks 테이블 생성
3. python chunk_documents.py 로 chunks_news.json 생성

실시간 자동 적재는 watch_documents.py 참고 (documents/ 폴더에 파일 추가 시 자동 실행).
"""

import json

from supabase_loader import embed_and_load_chunks

CHUNKS_PATH = "chunks_news.json"


def main():
    with open(CHUNKS_PATH, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"로드된 청크 수: {len(chunks)}")

    inserted = embed_and_load_chunks(chunks)
    print(f"적재 완료: {inserted} rows -> news_chunks")


if __name__ == "__main__":
    main()
