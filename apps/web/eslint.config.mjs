import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const config = [
  ...nextVitals,
  ...nextTs,
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
  {
    files: ["**/*.{ts,tsx,js,jsx}"],
    plugins: {
      "sim-tamy": {
        rules: {
          "no-thai-literals": {
            create(context) {
              const check = (node, value) => {
                if (/[\u0E00-\u0E7F]/u.test(value)) {
                  context.report({ node, message: "Thai strings belong in lib/i18n/th.json, content, or prompts." });
                }
              };
              return {
                Literal(node) { if (typeof node.value === "string") check(node, node.value); },
                TemplateElement(node) { check(node, node.value.raw); },
                JSXText(node) { check(node, node.value); },
              };
            },
          },
        },
      },
    },
    rules: { "sim-tamy/no-thai-literals": "error" },
  },
];

export default config;
