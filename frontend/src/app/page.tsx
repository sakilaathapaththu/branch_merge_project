import { getJson, money, MONTHS, num, pct } from "@/lib/api";
import { ErrorBox } from "@/components/ui";

type KPIs = {
  assets: number; deposits: number; income: number; expenses: number; profit: number;
  loans_count: number; loans_outstanding: number; par30_amount: number; par30_pct: number;
  savings: number; fixed_deposits: number; deposit_accounts: number; customers: number; as_of: string;
};
type Dashboard = {
  year: number;
  month: number;
  branches: { code: string; name: string; kpis: KPIs }[];
  consolidated: KPIs | null;
  trend: { month: string; income: number; expenses: number; profit: number }[];
};
type Health = { status: string; databases?: Record<string, string>; error?: string };

const ROWS: [string, keyof KPIs, (n: number) => string][] = [
  ["Total assets", "assets", money],
  ["Deposits (GL 401)", "deposits", money],
  ["Income (YTD)", "income", money],
  ["Expenses (YTD)", "expenses", money],
  ["Net profit (YTD)", "profit", money],
  ["Loans outstanding", "loans_outstanding", money],
  ["Number of loans", "loans_count", num],
  ["PAR > 30 days", "par30_pct", pct],
  ["Savings balance", "savings", money],
  ["Fixed deposits", "fixed_deposits", money],
  ["Deposit accounts", "deposit_accounts", num],
  ["Customers", "customers", num],
];

export default async function DashboardPage() {
  const [d, health] = await Promise.all([getJson<Dashboard>("/api/dashboard"), getJson<Health>("/api/health")]);
  if (!d) return <ErrorBox message="Could not load the dashboard. Is the backend running?" />;

  const cols = [
    ...d.branches.map((b) => ({ key: b.code, label: b.name, k: b.kpis })),
    ...(d.consolidated ? [{ key: "all", label: "Consolidated", k: d.consolidated }] : []),
  ];

  return (
    <>
      <h1 className="text-2xl font-bold">Dashboard</h1>
      <p className="text-sm text-gray-500">
        GL figures to end of {MONTHS[d.month - 1]} {d.year} · portfolio as at {cols[0]?.k.as_of} · LKR
      </p>

      <table className="mt-6 w-full text-sm">
        <thead>
          <tr className="border-b-2 text-left">
            <th className="py-1"></th>
            {cols.map((c) => <th key={c.key} className="text-right">{c.label}</th>)}
          </tr>
        </thead>
        <tbody>
          {ROWS.map(([label, key, f]) => (
            <tr key={key} className="border-b">
              <td className="py-1.5">{label}</td>
              {cols.map((c) => (
                <td key={c.key} className={`text-right tabular-nums ${c.key === "all" ? "font-semibold" : ""}`}>
                  {f(c.k[key] as number)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {d.consolidated && (
        <p className="mt-2 text-xs text-gray-500">Consolidated GL figures exclude inter-branch accounts (eliminated).</p>
      )}

      <h2 className="mt-8 font-semibold">Monthly income & expenses ({d.year})</h2>
      <table className="mt-2 w-full text-sm">
        <thead>
          <tr className="border-b-2 text-left">
            <th className="py-1">Month</th>
            <th className="text-right">Income</th>
            <th className="text-right">Expenses</th>
            <th className="text-right">Profit</th>
            <th className="w-1/3 pl-4"></th>
          </tr>
        </thead>
        <tbody>
          {(() => {
            const max = Math.max(1, ...d.trend.map((t) => Math.max(t.income, t.expenses)));
            return d.trend.map((t) => (
              <tr key={t.month} className="border-b border-gray-100">
                <td className="py-1">{t.month}</td>
                <td className="text-right tabular-nums">{money(t.income)}</td>
                <td className="text-right tabular-nums">{money(t.expenses)}</td>
                <td className={`text-right tabular-nums ${t.profit < 0 ? "text-red-700" : ""}`}>{money(t.profit)}</td>
                <td className="pl-4">
                  <div className="h-1.5 rounded bg-green-600" style={{ width: `${(t.income / max) * 100}%` }} />
                  <div className="mt-0.5 h-1.5 rounded bg-orange-500" style={{ width: `${(t.expenses / max) * 100}%` }} />
                </td>
              </tr>
            ));
          })()}
        </tbody>
      </table>
      <p className="mt-1 text-xs text-gray-500">Bars: green = income, orange = expenses.</p>

      <section className="mt-8 rounded-lg border p-4 text-sm">
        <h2 className="font-semibold">System status</h2>
        <p className="mt-1">
          API: <b>{health ? health.status : "unreachable"}</b>
          {health?.databases &&
            Object.entries(health.databases).map(([k, v]) => (
              <span key={k} className="ml-4">Branch {k}: {v}</span>
            ))}
        </p>
      </section>
    </>
  );
}
