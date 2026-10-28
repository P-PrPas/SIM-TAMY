import { StageDetail } from "@/components/platform/learn";

export default async function LearnStagePage({ params }: { params: Promise<{ stage: string }> }) {
  const { stage } = await params;
  return <StageDetail stage={decodeURIComponent(stage)} />;
}
