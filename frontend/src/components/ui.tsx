import { API_URL, BRANCHES, Group, money } from "@/lib/api";
import { PrintButton } from "./PrintButton";

/** GET form: branch selector + date field(s). Works without client JS. */
export function Filters({
  branch,
  dates,
  extra,
}: {
  branch: string;
  dates: { name: string; label: string; value: string }[];
  extra?: React.ReactNode;
}) {
  return (
    <form className="no-print mt-4 flex flex-wrap items-end gap-3 rounded-lg border p-3 text-sm">
      <label className="flex flex-col">
        Branch
        <select name="branch" defaultValue={branch} className="rounded border px-2 py-1">
          {BRANCHES.map((b) => (
            <option key={b.code} value={b.code}>
              {b.name}
            </option>
          ))}
        </select>
      </label>
      {dates.map((d) => (
        <label key={d.name} className="flex flex-col">
          {d.label}
          <input type="date" name={d.name} defaultValue={d.value} className="rounded border px-2 py-1" />
        </label>
      ))}
      {extra}
      <button className="rounded bg-blue-700 px-4 py-1.5 text-white">Show</button>
    </form>
  );
}

export function ReportHeader({ title, sub, exportQuery }: { title: string; sub: string; exportQuery?: string }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h1 className="text-2xl font-bold">{title}</h1>
        <p className="text-sm text-gray-500">{sub}</p>
      </div>
      <div className="no-print flex gap-2">
        {exportQuery && (
          <a href={`${API_URL}${exportQuery}`} className="rounded border px-3 py-1.5 text-sm hover:bg-gray-100">
            Export Excel
          </a>
        )}
        <PrintButton />
      </div>
    </div>
  );
}

export function Unavailable() {
  return <p className="mt-6 text-red-600">Could not load the report. Is the backend running?</p>;
}

export function Check({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs ${ok ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"}`}>
      {ok ? "✓" : "✗"} {label}
    </span>
  );
}

/** Grouped section (balance sheet / P&L) with account detail. */
export function Section({ title, groups, total }: { title: string; groups: Group[]; total: number }) {
  return (
    <table className="mt-6 w-full text-sm">
      <thead>
        <tr className="border-b-2 text-left">
          <th colSpan={2} className="py-1 text-base">{title}</th>
          <th className="text-right">Amount (LKR)</th>
        </tr>
      </thead>
      <tbody>
        {groups.map((g) => [
          <tr key={g.sortCode} className="bg-gray-50 font-semibold">
            <td className="py-1">{g.sortCode}</td>
            <td>{g.title}</td>
            <td className="text-right tabular-nums">{money(g.amount)}</td>
          </tr>,
          ...g.accounts.map((a) => (
            <tr key={g.sortCode + a.glAcc} className="text-gray-700">
              <td className="pl-4 font-mono text-xs">{a.code}</td>
              <td className="pl-4">{a.title}</td>
              <td className="text-right tabular-nums">{money(a.amount)}</td>
            </tr>
          )),
        ])}
        <tr className="border-t-2 font-bold">
          <td colSpan={2} className="py-1">Total {title}</td>
          <td className="text-right tabular-nums">{money(total)}</td>
        </tr>
      </tbody>
    </table>
  );
}
