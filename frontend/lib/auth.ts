import { headers } from "next/headers";

function secureEqual(left: string, right: string): boolean {
  const length = Math.max(left.length, right.length);
  let mismatch = left.length ^ right.length;
  for (let index = 0; index < length; index += 1) {
    mismatch |= (left.charCodeAt(index) || 0) ^ (right.charCodeAt(index) || 0);
  }
  return mismatch === 0;
}

export function configuredCredentials(): { username: string; password: string } | null {
  const username = process.env.APP_AUTH_USERNAME;
  const password = process.env.APP_AUTH_PASSWORD;
  if (!username || !password) return null;
  return { username, password };
}

export function isAuthorizationValid(value: string | null): boolean {
  const configured = configuredCredentials();
  const required = process.env.APP_ENV === "production" || configured !== null;
  if (!required) return true;
  if (!configured || !value?.startsWith("Basic ")) return false;
  try {
    const decoded = atob(value.slice(6));
    const separator = decoded.indexOf(":");
    if (separator < 0) return false;
    return (
      secureEqual(decoded.slice(0, separator), configured.username) &&
      secureEqual(decoded.slice(separator + 1), configured.password)
    );
  } catch {
    return false;
  }
}

export async function requireAuthenticatedOperator(): Promise<string> {
  const requestHeaders = await headers();
  if (!isAuthorizationValid(requestHeaders.get("authorization"))) {
    throw new Error("Authentication required");
  }
  return configuredCredentials()?.username ?? process.env.OPERATOR_ID ?? "local-operator";
}
