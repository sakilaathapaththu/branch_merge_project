import { cookies } from "next/headers";

export const COOKIE = "bm_token";

export type SessionUser = { username: string; fullName: string; role: "admin" | "viewer"; branch: "all" | "001" | "002" };

export async function getToken(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE)?.value;
}

/** Reads the user from the JWT for display only. The backend verifies the token on every call. */
export async function getUser(): Promise<SessionUser | null> {
  const token = await getToken();
  if (!token) return null;
  try {
    const p = JSON.parse(Buffer.from(token.split(".")[1], "base64url").toString());
    if (p.exp && p.exp * 1000 < Date.now()) return null;
    return { username: p.sub, fullName: p.name, role: p.role, branch: p.branch };
  } catch {
    return null;
  }
}

/** Branch a page should show: branch-bound users always get their own branch. */
export async function branchFor(requested: string | string[] | undefined): Promise<string> {
  const u = await getUser();
  if (u && u.branch !== "all") return u.branch;
  const b = Array.isArray(requested) ? requested[0] : requested;
  return b === "001" || b === "002" ? b : "all";
}
