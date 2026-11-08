import { BRANCHES, DEFAULT_DATE, getJson, money, one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { Check, Filters, ReportHeader, Unavailable } from "@/components/ui";

type TB = {
  lines: { glAcc: string; code: string; title: string; type: string; debit: number; credit: number; byBranch: Record<string, number> }[];
  totalDebit: number;
  totalCredit: number;
  balanced: boolean;
};

export default async function TrialBalance({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const branch = await branchFor(sp.branch);
  const date = one(sp.date, DEFAULT_DATE);
  const q = `date=${date}&branch=${branch}`;
  const tb = await getJson<TB>(`/api/reports/trial-balance?${q}`);
  const name = BRANCHES.find((b) => b.code === branch)?.name;
  const all = branch === "all";

  return (
    <>
      <ReportHeader title="Trial Balance" sub={`${name} · as of ${date} · LKR`} exportQuery={`/export/trial-balance?${q}`} />
      <Filters branch={branch} dates={[{ name: "date", label: "As of", value: date }]} />
      {!tb ? (
        <Unavailable />
      ) : (
        <>
          <div className="mt-4"><Check ok={tb.balanced} label={tb.balanced ? "Debits = Credits" : "Out of balance"} /></div>
          <table className="mt-3 w-full text-sm">
            <thead>
              <tr className="border-b-2 text-left">
                <th className="py-1">Code</th>
                <th>Account</th>
                {all && <th className="text-right">HO</th>}
                {all && <th className="text-right">Mahapitiya</th>}
                <th className="text-right">Debit</th>
                <th className="text-right">Credit</th>
              </tr>
            </thead>
            <tbody>
              {tb.lines.map((l) => (
                <tr key={l.glAcc} className="border-b border-gray-100">
                  <td className="py-0.5 font-mono text-xs">{l.code}</td>
                  <td>{l.title}</td>
                  {all && <td className="text-right tabular-nums text-gray-500">{money(l.byBranch["001"] ?? 0)}</td>}
                  {all && <td className="text-right tabular-nums text-gray-500">{money(l.byBranch["002"] ?? 0)}</td>}
                  <td className="text-right tabular-nums">{money(l.debit)}</td>
                  <td className="text-right tabular-nums">{money(l.credit)}</td>
                </tr>
              ))}
              <tr className="border-t-2 font-bold">
                <td colSpan={all ? 4 : 2} className="py-1">Total</td>
                <td className="text-right tabular-nums">{money(tb.totalDebit)}</td>
                <td className="text-right tabular-nums">{money(tb.totalCredit)}</td>
              </tr>
            </tbody>
          </table>
          {all && <p className="mt-2 text-xs text-gray-500">Branch columns show the net balance (debit +, credit −).</p>}
        </>
      )}
    </>
  );
}
