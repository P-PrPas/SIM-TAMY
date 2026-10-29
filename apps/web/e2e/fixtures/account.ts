import type { DemoAccount } from "../../lib/v2-api";
import { LOGIN_KEY } from "../../lib/demo-login";

/** Browser journeys start after demo login; login/logout journeys explicitly use an empty state. */
export function demoStorage(id = "parent-h-mom-1", role: DemoAccount["role"] = "learner", org_id = "org-demo-hospital") {
  return { cookies: [], origins: [{ origin: "http://127.0.0.1:3100", localStorage: [
    { name: LOGIN_KEY, value: JSON.stringify({ id, role, org_id, display_name_th: "Demo learner" }) },
    { name: "sim-tamy-demo-account", value: id },
  ] }] };
}
