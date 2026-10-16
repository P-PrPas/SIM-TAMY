import { createApi } from "./client";
import { readSession } from "../flow";

export function api() {
  return createApi({
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    getToken: () => readSession()?.token,
  });
}

/** Never read the learner token or persist the instructor secret for S8. */
export function instructorApi(secret: string) {
  return createApi({
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    getInstructorSecret: () => secret,
  });
}
