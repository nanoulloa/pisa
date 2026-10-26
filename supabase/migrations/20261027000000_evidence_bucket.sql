-- Private bucket for evidence videos. They show the user's own frames, so the engine deletes
-- them 24 hours after the check (modal_app.py runs the sweep hourly). Only the engine's secret
-- key reads and writes; clients get one-hour signed links from the engine.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('evidence', 'evidence', false, 16777216, array['video/mp4'])
on conflict (id) do update
set public = excluded.public,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;
