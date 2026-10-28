import { defineConfig } from "@playwright/test";

const apiUrl = "http://127.0.0.1:4010";
const webUrl = "http://127.0.0.1:3100";

export default defineConfig({
  testDir: "./e2e",
  testIgnore: ["**/*-live.spec.ts", "**/competition-demo.spec.ts"],
  timeout: 30_000,
  workers: 1,
  use: {
    baseURL: webUrl,
    channel: process.env.CI ? "chromium" : "chrome",
    viewport: { width: 360, height: 780 },
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "npx --yes @stoplight/prism-cli mock -p 4010 -h 127.0.0.1 docs/openapi.yaml",
      cwd: "../..",
      url: `${apiUrl}/v1/cases`,
      reuseExistingServer: !process.env.CI,
      timeout: 300_000,
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
