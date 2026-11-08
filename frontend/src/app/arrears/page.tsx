import Link from "next/link";
import { one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { ReportPage } from "@/components/ui";

const TABS = [
  ["ageing", "Ageing (PAR)"],
  ["list", "Loans in arrears"],
];

export default async function Arrears({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const branch = await branchFor(sp.branch);
  const view = one(sp.view, "ageing");
  const minDays = one(sp.min_days, "31");
  return (
    <>
      <div className="no-print mb-3 flex gap-4 text-sm">
        {TABS.map(([v, l]) => (
          <Link key={v} href={`/arrears?view=${v}&branch=${branch}`}
            className={v === view ? "font-semibold underline" : "text-blue-700 hover:underline"}>
            {l}
          </Link>
        ))}
      </div>
      {view === "list" ? (
        <ReportPage title="Loans in Arrears" apiPath="arrears-list" branch={branch} params={{ min_days: minDays }}
          fields={[{ kind: "number", name: "min_days", label: "Min. days", value: minDays }]}>
          <input type="hidden" name="view" value="list" />
        </ReportPage>
      ) : (
        <ReportPage title="Arrears Ageing" apiPath="arrears-ageing" branch={branch} params={{}} />
      )}
    </>
  );
}
