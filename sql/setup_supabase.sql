-- Supabase SQL Editor에서 1회 실행
-- 기존 프로젝트에 있던 documents / documents_test 테이블, match_documents_test 함수와
-- 이름이 겹치지 않도록 이번 병무청 보도자료 RAG 전용 이름(news_chunks / match_news_chunks)을 사용한다.

-- 1) pgvector 확장 활성화 (최초 1회, 이미 있으면 무시됨)
create extension if not exists vector;

-- 2) news_chunks 테이블
create table if not exists news_chunks (
  id bigserial primary key,
  content text,            -- 청크 원문 (프리픽스 없는 순수 본문)
  metadata jsonb,           -- source_file, document_title, press_date, section_heading, chunk_index
  embedding vector(1536)    -- OpenAI text-embedding-3-small = 1536차원
);

-- 3) 유사도 검색 함수 (naive RAG: 임베딩 코사인 유사도 기반 단일 단계 검색)
create or replace function match_news_chunks (
  query_embedding vector(1536),
  match_count int default null,
  filter jsonb default '{}'
) returns table (
  id bigint,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    content,
    metadata,
    1 - (news_chunks.embedding <=> query_embedding) as similarity
  from news_chunks
  where metadata @> filter
  order by news_chunks.embedding <=> query_embedding
  limit match_count;
end;
$$;
