import { CORE_PATH } from "./learning-path";
import type { Attempt, PassportLesson } from "./v2-api";

/** Completion records only; repeating a scenario never advances another stage or changes safety. */
export function learningProgress(attempts: readonly Attempt[], lessons: readonly PassportLesson[]) {
  const finished = new Set(attempts.filter((a) => a.finished_at).map((a) => a.story_id));
  const read = new Set(lessons.map((l) => l.unit_id));
  return CORE_PATH.map((core) => {
    const lessonDone = core.units.every((id) => read.has(id));
    const simulationDone = core.stories.every((id) => finished.has(id));
    return { ...core, lessonDone, simulationDone, completed: Number(lessonDone) + Number(simulationDone) };
  });
}
