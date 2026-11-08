import { NextRequest } from "next/server";
import { API_URL } from "@/lib/api";
import { getToken } from "@/lib/session";

const REPORTS = new Set(["trial-balance", "balance-sheet", "profit-loss"]);

/** Proxies Excel export so the browser never needs the token itself. */
export async function GET(req: NextRequest, { params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  if (!REPORTS.has(name)) return new Response("Not found", { status: 404 });
  const token = await getToken();
  if (!token) return new Response("Not logged in", { status: 401 });
  const res = await fetch(`${API_URL}/api/reports/${name}/export${req.nextUrl.search}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });
  return new Response(res.body, {
    status: res.status,
    headers: {
      "Content-Type": res.headers.get("Content-Type") ?? "application/octet-stream",
      "Content-Disposition": res.headers.get("Content-Disposition") ?? "attachment",
    },
  });
}
