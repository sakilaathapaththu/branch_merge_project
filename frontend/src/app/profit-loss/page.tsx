import { BRANCHES, DEFAULT_DATE, getJson, Group, money, one, SP } from "@/lib/api";
import { Filters, ReportHeader, Section, Unavailable } from "@/components/ui";

type PL = { income: Group[]; expenses: Group[]; totalIncome: number; totalExpenses: number; netProfit: number; note: string };

export default async function ProfitLoss({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const branch = one(sp.branch, "all");
  const to = one(sp.to, DEFAULT_DATE);
  const from = one(sp.from, `${to.slice(0, 4)}-01-01`);
  const q = `from=${from}&to=${to}&branch=${branch}`;
  const pl = await getJson<PL>(`/api/reports/profit-loss?${q}`);
  const name = BRANCHES.find((b) => b.code === branch)?.name;

  return (
    <>
      <ReportHeader title="Profit & Loss" sub={`${name} · ${from} to ${to} · LKR`} exportQuery={`/api/reports/profit-loss/export?${q}`} />
      <Filters
        branch={branch}
        dates={[
          { name: "from", label: "From", value: from },
          { name: "to", label: "To", value: to },
        ]}
      />
      {!pl ? (
        <Unavailable />
      ) : (
        <>
          <p className="mt-2 text-xs text-gray-500">{pl.note}</p>
          <Section title="Income" groups={pl.income} total={pl.totalIncome} />
          <Section title="Expenses" groups={pl.expenses} total={pl.totalExpenses} />
          <table className="mt-4 w-full text-base font-bold">
            <tbody>
              <tr className="border-t-4 border-double">
                <td className="py-1">Net profit</td>
                <td className="text-right tabular-nums">{money(pl.netProfit)}</td>
              </tr>
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
