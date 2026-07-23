import createClient from "openapi-fetch";
import type { paths } from "./schema";

// CSRF token echo + X-Workspace-Id header wiring is added in D6 (fetch-layer
// delivery). This client only establishes the typed baseline: same-origin
// credentials on every request, base URL from the environment.
const client = createClient<paths>({
  baseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
  credentials: "include",
});

export default client;
