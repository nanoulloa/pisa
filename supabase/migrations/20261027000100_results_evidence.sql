-- AnalysisResult gained `evidence` (required and nullable, like every contract property).
-- Results saved before it existed have none.
update public.results
set result = result || '{"evidence": null}'::jsonb
where not (result ? 'evidence');
