import { redirect } from "next/navigation";
import { getToken } from "./session";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const BRANCHES = [
  { code: "all", name: "Consolidated (All)" },
  { code: "001", name: "Head Office" },
  { code: "002", name: "Mahapitiya Branch" },
] as const;

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

const fmt2 = new Intl.NumberFormat("en-LK", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmt0 = new Intl.NumberFormat("en-LK", { maximumFractionDigits: 0 });

/** Money with brackets for negatives, as accountants print it. */
export const money = (n: number | null | undefined) =>
  n == null ? "" : Math.abs(n) < 0.005 ? "-" : n < 0 ? `(${fmt2.format(-n)})` : fmt2.format(n);
export const num = (n: number | null | undefined) => (n == null ? "" : fmt0.format(n));
export const pct = (n: number | null | undefined) => (n == null ? "" : `${n.toFixed(2)}%`);

export type SP = Promise<Record<string, string | string[] | undefined>>;
export const one = (v: string | string[] | undefined, d: string) =>
  (Array.isArray(v) ? v[0] : v) || d;

/** Common report shape returned by every /api/reports/* endpoint. */
export type Column = { key: string; label: string; type: "text" | "money" | "number" | "percent" | "date" };
export type Row = Record<string, string | number | null | undefined> & { _style?: string };
export type Report = { title: string; subtitle: string; columns: Column[]; rows: Row[]; notes: string[] };

export type Periods = { current_year: number; last_month: number; years: number[] };
export const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Fetch a report; returns the report or the API's error message. */
export async function getReport(path: string): Promise<Report | { error: string }> {
  const res = await api(path);
  if (!res) return { error: "Cannot reach the backend. Is it running?" };
  if (res.ok) return (await res.json()) as Report;
  try {
    const j = await res.json();
    return { error: typeof j.detail === "string" ? j.detail : `Error ${res.status}` };
  } catch {
    return { error: `Error ${res.status}` };
  }
}

/** Report periods, falling back to Oct 2026 if the API is unavailable. */
export async function getPeriods(): Promise<Periods> {
  return (await getJson<Periods>("/api/periods")) ?? { current_year: 2026, last_month: 10, years: [2026] };
}
