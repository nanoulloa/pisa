import { JobView } from "@/components/JobView";
import { resolveLocale } from "@/i18n/locale";

export default async function ResultPage({ params }: PageProps<"/[locale]/result/[id]">) {
  await resolveLocale(params);
  const { id } = await params;
  return <JobView id={id} />;
}
