import { createApi } from "./client";
import { readSession } from "../flow";

export function api() {
  return createApi({
    baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
    getToken: () => readSession()?.token,
  });
}
