import { getPeriods, one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { monthField, ReportPage, yearField } from "@/components/ui";

export default async function BalanceSheet({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const p = await getPeriods();
  const year = Number(one(sp.year, String(p.current_year)));
  const month = Number(one(sp.month, String(year === p.current_year ? p.last_month : 12)));
  const detail = one(sp.detail, "") === "true";
  return (
    <ReportPage
      title="Balance Sheet"
      apiPath="balance-sheet"
      branch={await branchFor(sp.branch)}
      params={{ year: String(year), month: String(month), detail: detail ? "true" : undefined }}
      fields={[
        yearField(p.years, year),
        monthField("month", "Month end", month),
        { kind: "checkbox", name: "detail", label: "Show accounts", checked: detail },
      ]}
    />
  );
}
