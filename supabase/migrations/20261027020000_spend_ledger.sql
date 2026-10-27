-- The spend ledger behind the engine's hard stop on paid Meta API calls, shared by every
-- container and every machine that runs the engine against this project.
--
-- Before a call, the engine holds its worst-case cost; after it, the hold is replaced by
-- what the call cost. A hold is granted only if everything spent plus everything held stays
-- under the cap, and holds are granted one at a time (a transaction-level advisory lock), so
-- concurrent calls cannot jointly cross the cap. A hold left by a container that died
-- mid-call stays counted: the call may have been billed.
--
-- RLS on with no policies, and the functions run as the caller: only the engine's secret
-- key can read the ledger or call them.

create table public.spend_entries (
  id bigint generated always as identity primary key,
  created_at timestamptz not null default now(),
  stage text not null,
  model text not null,
  unit text not null,
  quantity numeric not null check (quantity >= 0),
  usd numeric not null check (usd >= 0)
);

create table public.spend_holds (
  id uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  usd numeric not null check (usd >= 0)
);

alter table public.spend_entries enable row level security;
alter table public.spend_holds enable row level security;

create function public.spend_committed_usd()
returns numeric
language sql
stable
set search_path = ''
as $$
  select coalesce((select sum(usd) from public.spend_entries), 0)
       + coalesce((select sum(usd) from public.spend_holds), 0);
$$;

create function public.spend_spent_usd()
returns numeric
language sql
stable
set search_path = ''
as $$
  select coalesce(sum(usd), 0) from public.spend_entries;
$$;

-- The hold's id, or null when the call would not fit under the cap.
create function public.spend_reserve(p_usd numeric, p_cap_usd numeric)
returns uuid
language plpgsql
set search_path = ''
as $$
declare
  hold uuid;
begin
  if p_usd < 0 or p_cap_usd < 0 then
    raise exception 'amounts must not be negative';
  end if;
  perform pg_advisory_xact_lock(hashtext('pisa.spend'));
  if public.spend_committed_usd() + p_usd > p_cap_usd then
    return null;
  end if;
  insert into public.spend_holds (usd) values (p_usd) returning id into hold;
  return hold;
end;
$$;

-- Replaces a hold with what the call cost. A hold already settled or released is ignored,
-- so a retried settle never records a cost twice.
create function public.spend_settle(p_hold uuid, p_entries jsonb)
returns void
language plpgsql
set search_path = ''
as $$
begin
  perform pg_advisory_xact_lock(hashtext('pisa.spend'));
  delete from public.spend_holds where id = p_hold;
  if found then
    insert into public.spend_entries (stage, model, unit, quantity, usd)
    select e.stage, e.model, e.unit, e.quantity, e.usd
    from jsonb_to_recordset(p_entries)
      as e(stage text, model text, unit text, quantity numeric, usd numeric);
  end if;
end;
$$;

-- Frees a hold for a call that was never sent.
create function public.spend_release(p_hold uuid)
returns void
language plpgsql
set search_path = ''
as $$
begin
  perform pg_advisory_xact_lock(hashtext('pisa.spend'));
  delete from public.spend_holds where id = p_hold;
end;
$$;

revoke execute on function public.spend_committed_usd() from public, anon, authenticated;
revoke execute on function public.spend_spent_usd() from public, anon, authenticated;
revoke execute on function public.spend_reserve(numeric, numeric) from public, anon, authenticated;
revoke execute on function public.spend_settle(uuid, jsonb) from public, anon, authenticated;
revoke execute on function public.spend_release(uuid) from public, anon, authenticated;
grant execute on function public.spend_committed_usd() to service_role;
grant execute on function public.spend_spent_usd() to service_role;
grant execute on function public.spend_reserve(numeric, numeric) to service_role;
grant execute on function public.spend_settle(uuid, jsonb) to service_role;
grant execute on function public.spend_release(uuid) to service_role;
