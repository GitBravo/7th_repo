"""
documents/ 폴더의 병무청 보도자료(hwpx) 전체를 일괄 청킹해 chunks_news.json 으로 저장한다.
청킹 로직 자체는 hwpx_chunker.py 참고 (watch_documents.py와 공유).
"""

import glob
import json
import os

from hwpx_chunker import chunk_document

DOCS_DIR = "documents"
OUTPUT_PATH = "chunks_news.json"


def main():
    all_chunks = []
    for path in sorted(glob.glob(os.path.join(DOCS_DIR, "*.hwpx"))):
        doc_chunks = chunk_document(path)
        all_chunks.extend(doc_chunks)
        print(f"{os.path.basename(path)}: {len(doc_chunks)}개 청크")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n총 {len(all_chunks)}개 청크 -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
