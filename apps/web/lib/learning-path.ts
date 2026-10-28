// Navigation priorities only; availability and progress still come from the APIs.
export const CORE_PATH = [
  { stage: 1, units: ["KB-TM-ELEMENT-001", "KB-ANC-PLAN-001"], stories: ["thai-elements-family"] },
  { stage: 2, units: ["KB-IP-PLAN-001"], stories: ["thai-birth-conversation"] },
  { stage: 3, units: ["KB-PP-WARN-001", "KB-TM-REST-001", "KB-TM-SAFE-001"], stories: ["gs-a-postpartum-warning", "gs-b-thai-recovery"] },
  { stage: 4, units: ["KB-BF-COLOSTRUM-001", "KB-NB-WARN-001"], stories: ["thai-milk-family"] },
];

export const CORE_STORY_IDS = CORE_PATH.flatMap((s) => s.stories);
export const FOLLOW_UP_STORY_IDS = ["golden-first-night"];
