import type { ReactNode } from "react";

const paths: Record<string, ReactNode> = {
  family: <><circle cx="9" cy="7" r="3" /><path d="M3 21v-3a6 6 0 0 1 12 0v3M17 4a3 3 0 0 1 0 6m1 4a5 5 0 0 1 3 5v2" /></>,
  journey: <><path d="M4 19c0-8 16 0 16-9S4 17 4 5" /><circle cx="4" cy="4" r="2" /><circle cx="20" cy="20" r="2" /></>,
  bridge: <><path d="M3 19V9a4 4 0 0 1 8 0v10m2 0V9a4 4 0 0 1 8 0v10M1 19h22M7 12h10" /></>,
  lock: <><rect x="5" y="10" width="14" height="11" rx="3" /><path d="M8 10V7a4 4 0 0 1 8 0v3m-4 5v2" /></>,
  copy: <><rect x="8" y="8" width="12" height="13" rx="2" /><path d="M16 8V3H3v14h5" /></>,
  arrow: <path d="m5 12 14 0m-6-6 6 6-6 6" />,
  chevron: <path d="m6 9 6 6 6-6" />,
  book: <><path d="M12 5v15M3 4c4-1 6 0 9 2 3-2 5-3 9-2v15c-4-1-6 0-9 2-3-2-5-3-9-2Z" /></>,
  check: <path d="m5 12 4 4L20 5" />,
  shield: <><path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Z" /><path d="M12 7v6m0 3v1" /></>,
  heart: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />,
  leaf: <><path d="M20 3C5 2 2 9 6 15s15 4 14-12Z" /><path d="M3 21 15 9" /></>,
  chat: <path d="M21 11a9 9 0 0 1-9 9H3l2-5a9 9 0 1 1 16-4Z" />,
};

export function FamilyIcon({ name }: { name: string }) {
  return <svg className="family-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] ?? paths.family}</svg>;
}

/** Original illustration: two caregivers create one protected space around the baby. */
export function FamilyArtwork({ grandmother = false }: { grandmother?: boolean }) {
  return <svg viewBox="0 0 360 300" className="family-artwork" fill="none" aria-hidden="true">
    <path d="M58 262V145a122 122 0 0 1 244 0v117" fill="var(--color-brand-100)" />
    <path d="M35 261h290M43 238V140A137 137 0 0 1 317 140v98" stroke="var(--color-brand-300)" strokeWidth="1.5" />
    <circle cx="180" cy="104" r="48" fill="var(--color-canvas)" />
    {grandmother && <circle cx="112" cy="88" r="18" fill="var(--color-stone-400)" />}
    <path d="M77 254v-63a48 48 0 0 1 96 0v63" fill="var(--color-brand-600)" />
    <path d="M189 254v-63a47 47 0 0 1 94 0v63" fill="var(--color-brand-900)" />
    <path d="M92 119c0-43 65-45 65 0v23H92Z" fill={grandmother ? "var(--color-stone-400)" : "var(--color-brand-950)"} />
    <ellipse cx="125" cy="126" rx="24" ry="31" fill="var(--color-brand-200)" />
    <path d="M101 116c7 1 24-8 27-17 5 12 13 16 23 17" fill={grandmother ? "var(--color-stone-400)" : "var(--color-brand-950)"} />
    <path d="M207 112c0-35 56-39 59-1l-5 24h-50Z" fill="var(--color-brand-950)" />
    <ellipse cx="236" cy="126" rx="24" ry="31" fill="var(--color-brand-200)" />
    <path d="M212 111c13 4 30 0 39-9l11 17v-17l-29-12-21 9Z" fill="var(--color-brand-950)" />
    <path d="M119 133c4 3 8 3 12 0m99 0c4 3 8 3 12 0" stroke="var(--color-brand-800)" strokeWidth="2" strokeLinecap="round" />
    <path d="M111 195c16 33 38 41 69 42 30 0 52-15 66-42" stroke="var(--color-brand-200)" strokeWidth="20" strokeLinecap="round" />
    <path d="M145 214c0-18 16-34 35-34s35 16 35 34l-10 40h-50Z" fill="var(--color-canvas)" stroke="var(--color-brand-300)" strokeWidth="1.5" />
    <circle cx="180" cy="202" r="15" fill="var(--color-brand-200)" /><path d="M173 201q2 2 4 0m6 0q2 2 4 0m-10 8q3 3 6 0M162 226l36 17" stroke="var(--color-brand-800)" strokeWidth="1.5" strokeLinecap="round" />
    <path d="M175 79c-12-15-31 3 5 23 36-20 17-38 5-23l-5 5Z" fill="var(--color-gold)" />
    <path d="M38 251c-22-29-18-52-8-60 5 24 22 29 21 60m263 0c22-29 18-52 8-60-5 24-22 29-21 60" fill="var(--color-brand-200)" />
    <path d="M55 263h250" stroke="var(--color-brand-900)" strokeWidth="2" strokeLinecap="round" />
  </svg>;
}
