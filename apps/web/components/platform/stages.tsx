"use client";

import Link from "next/link";

import { t } from "@/lib/i18n";
import { CORE_PATH, storyReady, unitReady } from "@/lib/learning-path";
import { useV2 } from "@/lib/use-v2";
import { storyHref, v2 } from "@/lib/v2-api";

import { BACKDROPS, characterFrames, type Backdrop, type CharacterKey } from "../pixel/scene-art";
import { PALETTE, runs } from "../pixel/sprite";
import { Async } from "./shared";

const SCENES: Array<{ backdrop: Backdrop; left: CharacterKey; right: CharacterKey }> = [
  { backdrop: "sala", left: "ploy", right: "ton" },
  { backdrop: "veranda", left: "ploy", right: "yai" },
  { backdrop: "postpartumRoom", left: "non", right: "mali" },
  { backdrop: "consult", left: "ploy", right: "counselor" },
];

/** Decorative previews reuse the actual scenes without inventing dialogue, progress, or outcomes. */
export function StageArt({ stage }: { stage: number }) {
  const scene = SCENES[stage - 1];
  if (!scene) return null;
  return <svg className="pf-stage-art" viewBox="0 0 320 180" shapeRendering="crispEdges" aria-hidden="true">
    {BACKDROPS[scene.backdrop].map(([x, y, w, h, color], i) => <rect key={i} x={x} y={y} width={w} height={h} fill={PALETTE[color]} />)}
    {[scene.left, scene.right].map((who, i) => <g key={i} transform={`translate(${i === 0 ? 40 : 248} 100)`}>
      {runs(characterFrames(who, "idle")[0]!).map((r) => <rect key={`${r.x},${r.y}`} x={r.x} y={r.y} width={r.w} height={1} fill={r.fill} />)}
    </g>)}
  </svg>;
}

export function LearningStages() {
  const paths = useV2((s) => v2.learningPaths(s), "paths");
  const units = useV2((s) => v2.units(s), "units");
  const stories = useV2((s) => v2.stories(s), "stories");
  return <Async r={paths}>{(data) => data.stages.length === 0
    ? <p className="pf-note">{t("platform.learn.empty")}</p>
    : <>
      {(units.loading || units.error) && <Async r={units}>{() => null}</Async>}
      {(stories.loading || stories.error) && <Async r={stories}>{() => null}</Async>}
      <ol className="pf-list pf-stages">
      {CORE_PATH.map((core) => {
        const stage = data.stages.find((s) => String(s.stage) === String(core.stage));
        if (!stage) return null;
        const unit = units.data?.items.find((u) => core.units.includes(u.id) && unitReady(u.id));
        const story = stories.data?.find((s) => core.stories.includes(s.id) && storyReady(s.id));
        return <li key={core.stage} className="pf-stage-card">
          <StageArt stage={core.stage} />
          <div className="pf-stage-body">
            <span className="pf-kicker">{t("platform.learn.stageLabel")} {core.stage}</span>
            <h3><Link href={`/learn/${core.stage}`}>{stage.title_th}</Link></h3>
            <p className="pf-muted">{t(`platform.home.stage${core.stage}Text`)}</p>
            <Link href={`/learn/${core.stage}`} className="pf-link">{t("platform.learn.openStage")}</Link>
            <div className="pf-stage-start">
              {unit && <Link href={`/knowledge/${encodeURIComponent(unit.id)}`} className="pf-link">{t("platform.home.readLesson")}</Link>}
              {story && <Link href={storyHref(story.id)} className="pf-link">{t("platform.home.trySimulation")}</Link>}
            </div>
          </div>
        </li>;
      })}
    </ol></>}</Async>;
}
