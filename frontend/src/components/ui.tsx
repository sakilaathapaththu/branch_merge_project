import { BRANCHES, Column, getReport, money, MONTHS, num, pct, Report, Row } from "@/lib/api";
import { getUser } from "@/lib/session";
import { PrintButton } from "./PrintButton";

const input = "rounded border px-2 py-1";

export type Field =
  | { kind: "select"; name: string; label: string; value: string; options: { value: string; label: string }[] }
  | { kind: "date" | "text" | "number"; name: string; label: string; value: string; placeholder?: string; list?: string }
  | { kind: "checkbox"; name: string; label: string; checked: boolean };

export const yearField = (years: number[], value: number): Field => ({
  kind: "select", name: "year", label: "Year", value: String(value),
  options: years.map((y) => ({ value: String(y), label: String(y) })),
});

export const monthField = (name: string, label: string, value: number): Field => ({
  kind: "select", name, label, value: String(value),
  options: MONTHS.map((m, i) => ({ value: String(i + 1), label: m })),
});

/** GET form: branch selector + report-specific fields. Works without client JS. */
export async function Filters({ branch, fields = [], children }: { branch: string; fields?: Field[]; children?: React.ReactNode }) {
  const user = await getUser();
  const options = BRANCHES.filter((b) => !user || user.branch === "all" || b.code === user.branch);
  return (
    <form className="no-print mt-4 flex flex-wrap items-end gap-3 rounded-lg border p-3 text-sm">
      <label className="flex flex-col">
        Branch
        <select name="branch" defaultValue={branch} className={input}>
          {options.map((b) => (
            <option key={b.code} value={b.code}>{b.name}</option>
          ))}
        </select>
      </label>
      {fields.map((f) =>
        f.kind === "select" ? (
          <label key={f.name} className="flex flex-col">
            {f.label}
            <select name={f.name} defaultValue={f.value} className={input}>
              {f.options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </label>
        ) : f.kind === "checkbox" ? (
          <label key={f.name} className="flex items-center gap-1 pb-1.5">
            <input type="checkbox" name={f.name} value="true" defaultChecked={f.checked} /> {f.label}
          </label>
        ) : (
          <label key={f.name} className="flex flex-col">
            {f.label}
            <input type={f.kind} name={f.name} defaultValue={f.value} placeholder={f.placeholder} list={f.list} className={input} />
          </label>
        ),
      )}
      {children}
      <button className="rounded bg-blue-700 px-4 py-1.5 text-white">Show</button>
    </form>
  );
}

export function ReportHeader({ title, sub, exportHref }: { title: string; sub?: string; exportHref?: string }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2">
      <div>
        <h1 className="text-2xl font-bold">{title}</h1>
        {sub && <p className="text-sm text-gray-500">{sub}</p>}
      </div>
      <div className="no-print flex gap-2">
        {exportHref && (
          <a href={exportHref} className="rounded border px-3 py-1.5 text-sm hover:bg-gray-100">Export Excel</a>
        )}
        <PrintButton />
      </div>
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return <p className="mt-6 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">{message}</p>;
}

function cell(c: Column, v: Row[string]) {
  if (v == null || v === "") return "";
  if (typeof v === "number") {
    if (c.type === "money") return money(v);
    if (c.type === "number") return num(v);
    if (c.type === "percent") return pct(v);
  }
  return String(v);
}

const ROW_STYLE: Record<string, string> = {
  heading: "font-bold text-base pt-3",
  subheading: "bg-gray-50 font-semibold",
  subtotal: "border-t font-semibold",
  total: "border-t-2 border-b-2 border-gray-700 font-bold bg-blue-50",
  detail: "text-gray-700",
};

/** Renders any report in the common shape {title, subtitle, columns, rows, notes}. */
export function ReportTable({ report }: { report: Report }) {
  const cols = report.columns;
  return (
    <>
      <p className="mt-3 text-sm text-gray-600">{report.subtitle}</p>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b-2 text-left">
              {cols.map((c) => (
                <th key={c.key} className={`px-1 py-1 ${["money", "number", "percent"].includes(c.type) ? "text-right" : ""}`}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {report.rows.map((r, i) => (
              <tr key={i} className={`border-b border-gray-100 ${ROW_STYLE[r._style ?? ""] ?? ""}`}>
                {cols.map((c, j) => (
                  <td
                    key={c.key}
                    className={`px-1 py-0.5 ${["money", "number", "percent"].includes(c.type) ? "whitespace-nowrap text-right tabular-nums" : ""} ${
                      r._style === "detail" && j === 1 ? "pl-5" : ""
                    } ${c.type === "date" ? "whitespace-nowrap" : ""}`}
                  >
                    {cell(c, r[c.key])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {report.notes.length > 0 && (
        <ul className="mt-3 space-y-0.5 text-xs text-gray-600">
          {report.notes.map((n) => (
            <li key={n} className={n.startsWith("⚠") ? "font-semibold text-red-700" : ""}>{n}</li>
          ))}
        </ul>
      )}
    </>
  );
}

/** Page body for one report: header with export, filters, table or error. */
export async function ReportPage({
  title, apiPath, params, branch, fields, children,
}: {
  title: string;
  apiPath: string; // e.g. "trial-balance"
  params: Record<string, string | undefined>;
  branch: string;
  fields?: Field[];
  children?: React.ReactNode;
}) {
  const q = new URLSearchParams({ branch });
  for (const [k, v] of Object.entries(params)) if (v) q.set(k, v);
  const rep = await getReport(`/api/reports/${apiPath}?${q}`);
  return (
    <>
      <ReportHeader title={"error" in rep ? title : rep.title} exportHref={"error" in rep ? undefined : `/export/${apiPath}?${q}`} />
      <Filters branch={branch} fields={fields}>{children}</Filters>
      {"error" in rep ? <ErrorBox message={rep.error} /> : <ReportTable report={rep} />}
    </>
  );
}
