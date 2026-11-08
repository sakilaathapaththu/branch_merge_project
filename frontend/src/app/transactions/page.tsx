import { getPeriods, one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { Field, Filters, ReportHeader, ReportPage } from "@/components/ui";

export default async function Transactions({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const p = await getPeriods();
  const branch = await branchFor(sp.branch);
  const lastDay = new Date(Date.UTC(p.current_year, p.last_month, 0)).toISOString().slice(0, 10);
  const from = one(sp.date_from, lastDay);
  const to = one(sp.date_to, lastDay);
  const acc = one(sp.acc, "");
  const fields: Field[] = [
    { kind: "date", name: "date_from", label: "From", value: from },
    { kind: "date", name: "date_to", label: "To", value: to },
    { kind: "text", name: "acc", label: "Account no.", value: acc, placeholder: "optional" },
  ];
  if (!sp.date_from) {
    return (
      <>
        <ReportHeader title="Customer Transactions" sub="Up to 31 days at a time, or any range for one account." />
        <Filters branch={branch} fields={fields} />
      </>
    );
  }
  return (
    <ReportPage title="Customer Transactions" apiPath="transactions" branch={branch}
      params={{ date_from: from, date_to: to, acc: acc || undefined }} fields={fields} />
  );
}
