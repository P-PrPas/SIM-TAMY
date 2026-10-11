import th from "./th.json";

/** Look up a Thai string by dotted key, e.g. t("banner.educationOnly"). Throws on a missing key. */
export function t(key: string): string {
  let node: unknown = th;
  for (const part of key.split(".")) {
    if (typeof node !== "object" || node === null || !(part in node)) {
      throw new Error(`Missing i18n key: ${key}`);
    }
    node = (node as Record<string, unknown>)[part];
  }
  if (typeof node !== "string") throw new Error(`i18n key is not a string: ${key}`);
  return node;
}
