import { getPeriods, one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { monthField, ReportPage, yearField } from "@/components/ui";

export default async function IncomeStatement({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const p = await getPeriods();
  const year = Number(one(sp.year, String(p.current_year)));
  const to = Number(one(sp.to_month, String(year === p.current_year ? p.last_month : 12)));
  const from = Number(one(sp.from_month, "1"));
  const detail = one(sp.detail, "") === "true";
  return (
    <ReportPage
      title="Profit & Loss"
      apiPath="income-statement"
      branch={await branchFor(sp.branch)}
      params={{
        year: String(year),
        from_month: String(from),
        to_month: String(to),
        detail: detail ? "true" : undefined,
      }}
      fields={[
        yearField(p.years, year),
        monthField("from_month", "From", from),
        monthField("to_month", "To", to),
        { kind: "checkbox", name: "detail", label: "Show accounts", checked: detail },
      ]}
    />
  );
}
