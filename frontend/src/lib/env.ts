/**
 * Validated, typed access to environment variables.
 *
 * Fails fast at startup if a required variable is missing, rather than
 * letting `undefined` silently propagate into API calls.
 */

function requireEnv(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(
      `Missing required environment variable: ${name}. Copy .env.local.example to .env.local and set it.`
    );
  }
  return value;
}

export const env = {
  apiBaseUrl: requireEnv(
    "NEXT_PUBLIC_API_BASE_URL",
    process.env.NEXT_PUBLIC_API_BASE_URL
  ),
};