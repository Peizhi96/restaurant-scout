import type { NextRequest } from "next/server";

import { configuredCredentials, isAuthorizationValid } from "@/lib/auth";

export function proxy(request: NextRequest) {
  if (process.env.APP_ENV === "production" && configuredCredentials() === null) {
    return new Response("Application authentication is not configured", {
      status: 503,
      headers: { "Cache-Control": "no-store" },
    });
  }
  if (!isAuthorizationValid(request.headers.get("authorization"))) {
    return new Response("Authentication required", {
      status: 401,
      headers: {
        "WWW-Authenticate": 'Basic realm="Restaurant Scout", charset="UTF-8"',
        "Cache-Control": "no-store",
      },
    });
  }
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
