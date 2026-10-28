import { KnowledgeUnit } from "@/components/platform/knowledge";

export default async function KnowledgeUnitPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <KnowledgeUnit id={decodeURIComponent(id)} />;
}
