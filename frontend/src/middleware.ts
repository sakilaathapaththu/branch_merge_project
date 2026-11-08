import { NextRequest, NextResponse } from "next/server";

const COOKIE = "bm_token";

/** Every page needs a login cookie; the backend still verifies the token itself. */
export function middleware(req: NextRequest) {
  if (req.cookies.get(COOKIE)) return NextResponse.next();
  const url = req.nextUrl.clone();
  url.pathname = "/login";
  url.search = `?next=${encodeURIComponent(req.nextUrl.pathname + req.nextUrl.search)}`;
  return NextResponse.redirect(url);
}

export const config = {
  matcher: ["/((?!login|_next/|favicon.ico).*)"],
};
