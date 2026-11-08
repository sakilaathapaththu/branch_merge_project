import { NextRequest } from "next/server";
import { API_URL } from "@/lib/api";
import { getToken } from "@/lib/session";

const REPORTS = new Set([
  "trial-balance", "balance-sheet", "income-statement", "gl-ledger", "loan-portfolio",
  "arrears-ageing", "arrears-list", "deposits", "transactions",
]);

/** Excel export: proxies /api/reports/<name>?…&format=xlsx with the user's token. */
export async function GET(req: NextRequest, { params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  if (!REPORTS.has(name)) return new Response("Not found", { status: 404 });
  const token = await getToken();
  if (!token) return new Response("Not logged in", { status: 401 });
  const q = new URLSearchParams(req.nextUrl.searchParams);
  q.set("format", "xlsx");
  const res = await fetch(`${API_URL}/api/reports/${name}?${q}`, {
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
