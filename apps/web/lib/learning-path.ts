// The ready-to-use slice: one lesson and one scenario per stage. Every learner entry point (stage page, lab,
// knowledge index, direct URLs, assignments) reads availability from here; anything not listed is shown greyed
// out and cannot be opened. Content, APIs and progress are untouched. To open more, add ids to a stage.
export const CORE_PATH = [
  { stage: 1, units: ["KB-TM-ELEMENT-001"], stories: ["thai-elements-family"] },
  { stage: 2, units: ["KB-IP-HERITAGE-001"], stories: ["thai-birth-conversation"] },
  { stage: 3, units: ["KB-PP-WARN-001"], stories: ["gs-a-postpartum-warning"] },
  { stage: 4, units: ["KB-BF-COLOSTRUM-001"], stories: ["thai-milk-family"] },
];

export const CORE_STORY_IDS = CORE_PATH.flatMap((s) => s.stories);
const CORE_UNIT_IDS = CORE_PATH.flatMap((s) => s.units);

// Dev, CI and instructors can reach everything with NEXT_PUBLIC_SHOW_ALL_CONTENT=true (read per call so tests can toggle it).
const showAll = () => process.env.NEXT_PUBLIC_SHOW_ALL_CONTENT === "true";
export const unitReady = (id: string) => showAll() || CORE_UNIT_IDS.includes(id);
export const storyReady = (id: string) => showAll() || CORE_STORY_IDS.includes(id);
