-- Jobs and their results. Mirrors Job and AnalysisResult in packages/contracts/schema/pisa.schema.json.
-- Only the engine reads and writes these tables, with the secret key (which bypasses RLS).
-- RLS is on with no policies, so the publishable key and browsers can read or write nothing.

create table public.jobs (
  id uuid primary key,
  created_at timestamptz not null,
  source text not null check (source in ('web', 'whatsapp', 'eval')),
  locale text not null check (locale in ('en', 'es', 'zh-CN', 'pt-BR')),
  data_policy text not null check (data_policy in ('user', 'internal')),
  status text not null check (status in ('queued', 'running', 'done', 'failed')),
  stage text check (
    stage in ('ingest', 'plan', 'track', 'stabilize', 'measure', 'test', 'verdict', 'explain', 'render')
  ),
  error jsonb
);

create index jobs_created_at_idx on public.jobs (created_at);

-- Derived measurements only. Raw videos never reach the database.
create table public.results (
  job_id uuid primary key references public.jobs (id) on delete cascade,
  created_at timestamptz not null default now(),
  result jsonb not null
);

alter table public.jobs enable row level security;
alter table public.results enable row level security;
