-- AnalysisResult gained `stabilization` (required and nullable, like every contract property).
-- Results saved before it existed had no camera path, so they get null.
update public.results
set result = result || '{"stabilization": null}'::jsonb
where not (result ? 'stabilization');
