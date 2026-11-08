import { redirect } from "next/navigation";
import { getToken } from "./session";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const BRANCHES = [
  { code: "all", name: "Consolidated (All)" },
  { code: "001", name: "Head Office" },
  { code: "002", name: "Mahapitiya Branch" },
] as const;

export const DEFAULT_DATE = "2026-10-31";

/** Server-side API call with the user's token. 401 → back to the login page. */
export async function api(path: string, init: RequestInit = {}): Promise<Response | null> {
  const token = await getToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      cache: "no-store",
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    return null;
  }
  if (res.status === 401) redirect("/login?expired=1");
  return res;
}

export async function getJson<T>(path: string): Promise<T | null> {
  const res = await api(path);
  return res?.ok ? ((await res.json()) as T) : null;
}

const fmt = new Intl.NumberFormat("en-LK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const money = (n: number | null | undefined) => (n ? fmt.format(n) : n === 0 ? "-" : "");

export type SP = Promise<Record<string, string | string[] | undefined>>;
export const one = (v: string | string[] | undefined, d: string) =>
  (Array.isArray(v) ? v[0] : v) || d;

export type Group = {
  sortCode: string;
  title: string;
  amount: number;
  accounts: { glAcc: string; code: string; title: string; amount: number }[];
};
