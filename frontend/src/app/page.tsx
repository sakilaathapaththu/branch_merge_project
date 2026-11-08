import { DEFAULT_DATE, getJson, money, one, SP } from "@/lib/api";
import { Check } from "@/components/ui";
import { getUser } from "@/lib/session";

type Health = { status: string; databases?: Record<string, string>; error?: string };
type BS = { totalAssets: number; totalLiabilities: number; totalEquity: number; currentYearProfit: number; balanced: boolean };
type PL = { totalIncome: number; totalExpenses: number; netProfit: number };

const ALL_COLS = [
  ["001", "Head Office"],
  ["002", "Mahapitiya"],
  ["all", "Consolidated"],
] as const;

export default async function Dashboard({ searchParams }: { searchParams: SP }) {
  const date = one((await searchParams).date, DEFAULT_DATE);
  const yearStart = `${date.slice(0, 4)}-01-01`;
  const user = await getUser();
  const COLS = ALL_COLS.filter(([b]) => !user || user.branch === "all" || b === user.branch);
  const health = await getJson<Health>("/api/health");
  const data = await Promise.all(
    COLS.map(async ([b]) => ({
      bs: await getJson<BS>(`/api/reports/balance-sheet?date=${date}&branch=${b}`),
      pl: await getJson<PL>(`/api/reports/profit-loss?from=${yearStart}&to=${date}&branch=${b}`),
    })),
  );

  const rows: [string, (i: number) => number | undefined][] = [
    ["Total assets", (i) => data[i].bs?.totalAssets],
    ["Total liabilities", (i) => data[i].bs?.totalLiabilities],
    ["Equity", (i) => data[i].bs?.totalEquity],
    ["Income (YTD)", (i) => data[i].pl?.totalIncome],
    ["Expenses (YTD)", (i) => data[i].pl?.totalExpenses],
    ["Net profit (YTD)", (i) => data[i].pl?.netProfit],
  ];

  return (
    <>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-sm text-gray-500">Key figures as of {date} (LKR)</p>

      <form className="mt-4 flex items-end gap-2 text-sm">
        <label className="flex flex-col">
          As of
          <input type="date" name="date" defaultValue={date} className="rounded border px-2 py-1" />
        </label>
        <button className="rounded bg-blue-700 px-4 py-1.5 text-white">Show</button>
      </form>

      <table className="mt-6 w-full text-sm">
        <thead>
          <tr className="border-b-2 text-left">
            <th className="py-1"></th>
            {COLS.map(([c, n]) => (
              <th key={c} className="text-right">{n}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, f]) => (
            <tr key={label} className="border-b">
              <td className="py-1.5">{label}</td>
              {COLS.map(([c], i) => (
                <td key={c} className="text-right tabular-nums">{money(f(i))}</td>
              ))}
            </tr>
          ))}
          <tr>
            <td className="py-1.5">Balance sheet balances</td>
            {COLS.map(([c], i) => (
              <td key={c} className="text-right">
                {data[i].bs && <Check ok={data[i].bs!.balanced} label={data[i].bs!.balanced ? "Yes" : "No"} />}
              </td>
            ))}
          </tr>
        </tbody>
      </table>

      <section className="mt-8 rounded-lg border p-4 text-sm">
        <h2 className="font-semibold">System status</h2>
        <p className="mt-1">
          API: <b>{health ? health.status : "unreachable"}</b>
          {health?.databases &&
            Object.entries(health.databases).map(([k, v]) => (
              <span key={k} className="ml-4">Branch {k}: {v}</span>
            ))}
        </p>
        {health?.error && <p className="text-red-600">{health.error}</p>}
      </section>
    </>
  );
}
