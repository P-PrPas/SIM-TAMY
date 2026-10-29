import { defineConfig } from "@playwright/test";
import { demoStorage } from "./e2e/fixtures/account";

const apiUrl = "http://127.0.0.1:8000";
const webUrl = "http://127.0.0.1:3100";

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["**/journeys-live.spec.ts", "**/family-live.spec.ts", "**/family-golden-live.spec.ts", "**/account-dashboard-live.spec.ts"],
  timeout: 120_000,
  workers: 1,
  use: {
    baseURL: webUrl,
    storageState: demoStorage(),
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
        CORS_ORIGINS: webUrl,
      },
      url: `${apiUrl}/health`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --hostname 127.0.0.1 --port 3100",
      cwd: ".",
      // e2e covers every story, including the ones the learner UI greys out (lib/learning-path.ts)
      env: { NEXT_PUBLIC_API_URL: apiUrl, NEXT_PUBLIC_SHOW_ALL_CONTENT: "true" },
      url: webUrl,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
