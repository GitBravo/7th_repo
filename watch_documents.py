"""
documents/ 폴더를 실시간으로 감시하다가 새 hwpx 파일이 추가되면
자동으로 청킹 -> 임베딩 -> Supabase news_chunks 적재까지 수행한다.

단독 실행: python watch_documents.py (Ctrl+C로 종료)
웹 서버에 내장: backend.py의 FastAPI startup 이벤트에서 start_watcher() 호출
"""

import os
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from hwpx_chunker import chunk_document
from supabase_loader import embed_and_load_chunks

DOCS_DIR = "documents"


def _wait_until_stable(path, interval=0.5, required_checks=3, timeout=30):
    """파일 복사/다운로드가 끝날 때까지(크기 변화가 멈출 때까지) 대기."""
    last_size = -1
    stable_count = 0
    waited = 0.0
    while stable_count < required_checks and waited < timeout:
        try:
            size = os.path.getsize(path)
        except OSError:
            size = -1
        if size == last_size and size >= 0:
            stable_count += 1
        else:
            stable_count = 0
            last_size = size
        time.sleep(interval)
        waited += interval


class HwpxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory:
            self._handle(event.src_path)

    def on_moved(self, event):
        # 임시 파일명으로 복사 후 rename 하는 저장 방식(예: 브라우저 다운로드) 대응
        if not event.is_directory:
            self._handle(event.dest_path)

    def _handle(self, path):
        if not path.lower().endswith(".hwpx"):
            return
        filename = os.path.basename(path)
        try:
            _wait_until_stable(path)
            print(f"[watch] 새 문서 감지: {filename}")
            chunks = chunk_document(path)
            inserted = embed_and_load_chunks(chunks)
            print(f"[watch] 적재 완료: {filename} ({inserted}개 청크 -> news_chunks)")
        except Exception as e:
            print(f"[watch] 처리 실패: {filename} - {e}")


def start_watcher():
    os.makedirs(DOCS_DIR, exist_ok=True)
    observer = Observer()
    observer.schedule(HwpxHandler(), DOCS_DIR, recursive=False)
    observer.daemon = True
    observer.start()
    print(f"[watch] '{DOCS_DIR}' 폴더 실시간 감시 시작")
    return observer


if __name__ == "__main__":
    watcher = start_watcher()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        watcher.stop()
    watcher.join()
