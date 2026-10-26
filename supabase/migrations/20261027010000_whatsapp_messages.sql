-- WhatsApp message ids already handled. Meta retries webhook deliveries for days, so the
-- engine claims each id once. Only ids and times: no phone numbers, no content. Rows older
-- than 7 days are deleted by the hourly sweep. RLS on with no policies: only the engine's
-- secret key reads and writes.
create table public.whatsapp_messages (
  id text primary key,
  received_at timestamptz not null default now()
);

create index whatsapp_messages_received_at_idx on public.whatsapp_messages (received_at);

alter table public.whatsapp_messages enable row level security;
