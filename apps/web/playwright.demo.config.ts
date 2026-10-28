import { defineConfig } from "@playwright/test";

// Stage golden path (C02): same stack as playwright.live.config.ts plus the offline Replay gallery.
// Needs a migrated PostgreSQL in DATABASE_URL; the LLM is always the mock provider.
const apiUrl = "http://127.0.0.1:8000";
const webUrl = "http://127.0.0.1:3100";

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["**/competition-demo.spec.ts", "**/golden-scenarios.spec.ts", "**/thai-curriculum-live.spec.ts"],
  timeout: 180_000,
  expect: { timeout: 15_000 }, // the first visit to a route in `next dev` compiles it
  workers: 1,
  retries: process.env.CI ? 1 : 0, // first route visit in `next dev` can compile past the expect timeout
  use: {
    baseURL: webUrl,
    channel: process.env.CI ? "chromium" : "chrome",
    viewport: { width: 360, height: 780 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `${process.env.SIMTAMY_PYTHON ?? "python"} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: "../api",
      env: {
        CONTENT_DIR: "../../content",
        ALLOW_DRAFT_CASES: "true",
        LLM_PROVIDER: "mock",
        MOCK_LLM_SCRIPT: "tests/fixtures/mock_interpreter_invalid.yaml",
        RATE_LIMIT_PER_MIN: "0",
        ENABLE_REPLAY: "true",
        CORS_ORIGINS: webUrl,
      },
      url: `${apiUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
      cwd: ".",
      env: { NEXT_PUBLIC_API_URL: apiUrl },
      url: webUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
