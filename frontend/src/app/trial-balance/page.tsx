import { getPeriods, one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { monthField, ReportPage, yearField } from "@/components/ui";

export default async function TrialBalance({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const p = await getPeriods();
  const year = Number(one(sp.year, String(p.current_year)));
  const month = Number(one(sp.month, String(year === p.current_year ? p.last_month : 12)));
  const showZero = one(sp.show_zero, "") === "true";
  return (
    <ReportPage
      title="Trial Balance"
      apiPath="trial-balance"
      branch={await branchFor(sp.branch)}
      params={{ year: String(year), month: String(month), show_zero: showZero ? "true" : undefined }}
      fields={[
        yearField(p.years, year),
        monthField("month", "Month end", month),
        { kind: "checkbox", name: "show_zero", label: "Show zero balances", checked: showZero },
      ]}
    />
  );
}
