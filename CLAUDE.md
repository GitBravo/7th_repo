## 개요
- RAG 기반 문서 검색·답변 AI 질의응답 채팅 웹 시스템을 구현하려고 한다.

## 제약조건
- AI 채팅 모델은 OpenRouter를 활용해 연동한다.
- 임베딩 모델은 open AI의 embedding-small 사용한다.
- RAG에 임베딩 할 문서는 documents 폴더의 hwpx 파일이다. (최초 10개로 시작했으나, 아래
  "실시간 자동 임베딩" 기능으로 documents 폴더에 파일이 추가되는 대로 계속 늘어날 수 있음 -
  "10개 고정"이 아니라 "documents 폴더 전체"로 해석할 것)
- 벡터 DB는 supabase를 사용한다. (vectorDB는 SQL 구문 작성 시 테이블과 함수 명을 겹치지 않게 구성할 것)
- Rerank는 Cohere Rerank 모델 활용
- RAG 방식은 Naive RAG 방식을 사용
- **(추가) 실시간 자동 임베딩**: documents 폴더에 새 hwpx 파일이 추가되면 사람이 스크립트를 실행하지
  않아도 자동으로 청킹 → 임베딩 → Supabase 적재까지 실시간으로 처리되어야 한다.
  (구현: `watch_documents.py` - watchdog 기반 폴더 감시, `backend.py` 서버 기동 시 자동 시작)
- **(추가) 프론트엔드 디자인**: 웹 UI는 Tailwind CSS 기반의 커스텀 디자인을 적용한다.
  Streamlit은 자체 렌더링 구조상 Tailwind를 표준적으로 적용하기 어려워, FastAPI(`backend.py`) +
  정적 HTML/JS(`static/`) + Tailwind CDN 조합으로 구현한다 (RAG 로직 자체는 수정하지 않고 재사용).

## 작업절차
1. hwpx 문서를 먼저 읽고 어떤 청킹 전략이 좋을지 문서에 최적화된 전략을 설명 후 제안할 것
2. 결정된 청킹 전략에 따라 청킹 한 뒤 Supabase에 임베딩 데이터를 적재하는 Python 코드 작성할 것
3. 그 후 추가적인 사전 작업 절차가 있다면 추가 제안하고, 사전 작업이 더이상 없다면 전체 작업 절차를 나에게 설명한 후 차례대로 실행하되 내가 해야 할 부분은 중간에 멈추고 설명할 것
4. (완료, 1~3의 결과물 위에 추가) documents 폴더 실시간 감시 + 자동 임베딩 기능 추가, 이후 기능은
   건드리지 않고 웹 UI 디자인만 Tailwind CSS 기반으로 개편

## 기타
- 혹시 내 가이드에 부족한 부분이 있거나 구현에 애매한 부분이 있다면 짐작하지 말고 바로 멈춘 뒤, 나에게 다시 되물을 것 (예를들어 SUPABASE_URL, API KEY 등이 필요한 경우)
- 각 과정마다 의사 결정된 내용과 이유를 PLAN.md 파일을 생성해서 기록할 것
- API KEY, URL 등 민감 정보는 GIT 에 커밋하지 않도록 별도 파일로 분리해서 예외처리 할 것

## API 키 관련
- 모든 키/URL은 `.env` 파일(git 미추적)에 보관한다.
- 필요한 키: `SUPABASE_URL`, `SUPABASE_KEY`(service_role), `OPENAI_API_KEY`, `OPENROUTER_API_KEY`,
  `COHERE_API_KEY` - 전부 설정 완료 (Cohere는 트라이얼 키, 소규모 테스트 용도)