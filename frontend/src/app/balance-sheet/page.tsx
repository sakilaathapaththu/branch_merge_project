import { BRANCHES, DEFAULT_DATE, getJson, Group, money, one, SP } from "@/lib/api";
import { Check, Filters, ReportHeader, Section, Unavailable } from "@/components/ui";

type BS = {
  assets: Group[];
  liabilities: Group[];
  equity: Group[];
  totalAssets: number;
  totalLiabilities: number;
  totalEquity: number;
  currentYearProfit: number;
  totalLiabilitiesAndEquity: number;
  balanced: boolean;
};

export default async function BalanceSheet({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const branch = one(sp.branch, "all");
  const date = one(sp.date, DEFAULT_DATE);
  const q = `date=${date}&branch=${branch}`;
  const bs = await getJson<BS>(`/api/reports/balance-sheet?${q}`);
  const name = BRANCHES.find((b) => b.code === branch)?.name;

  return (
    <>
      <ReportHeader title="Balance Sheet" sub={`${name} · as of ${date} · LKR`} exportQuery={`/api/reports/balance-sheet/export?${q}`} />
      <Filters branch={branch} dates={[{ name: "date", label: "As of", value: date }]} />
      {!bs ? (
        <Unavailable />
      ) : (
        <>
          <div className="mt-4"><Check ok={bs.balanced} label={bs.balanced ? "Assets = Liabilities + Equity" : "Does not balance"} /></div>
          <Section title="Assets" groups={bs.assets} total={bs.totalAssets} />
          <Section title="Liabilities" groups={bs.liabilities} total={bs.totalLiabilities} />
          <Section title="Equity" groups={bs.equity} total={bs.totalEquity} />
          <table className="mt-4 w-full text-sm font-semibold">
            <tbody>
              <tr><td className="py-1">Current year profit (not yet closed)</td><td className="text-right tabular-nums">{money(bs.currentYearProfit)}</td></tr>
              <tr className="border-t-2"><td className="py-1">Total liabilities + equity</td><td className="text-right tabular-nums">{money(bs.totalLiabilitiesAndEquity)}</td></tr>
            </tbody>
          </table>
        </>
      )}
    </>
  );
}
