-- AnalysisResult gained `explanation` (required and nullable, like every contract property).
-- Results saved before it existed have none, so clients show their templated copy.
update public.results
set result = result || '{"explanation": null}'::jsonb
where not (result ? 'explanation');
