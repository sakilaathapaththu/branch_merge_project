import { getJson, getPeriods, one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { Field, Filters, ReportHeader, ReportPage } from "@/components/ui";

type GLAcc = { gl: string; title: string };

export default async function GLLedger({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const p = await getPeriods();
  const branch = await branchFor(sp.branch);
  const gl = one(sp.gl_code, "");
  const from = one(sp.date_from, `${p.current_year}-01-01`);
  const to = one(sp.date_to, `${p.current_year}-12-31`);
  const accounts = (await getJson<GLAcc[]>("/api/gl/accounts")) ?? [];
  const fields: Field[] = [
    { kind: "text", name: "gl_code", label: "GL code", value: gl, placeholder: "e.g. 311010101", list: "gl-list" },
    { kind: "date", name: "date_from", label: "From", value: from },
    { kind: "date", name: "date_to", label: "To", value: to },
  ];
  const list = (
    <datalist id="gl-list">
      {accounts.map((a) => (
        <option key={a.gl} value={a.gl}>{a.title}</option>
      ))}
    </datalist>
  );
  if (!gl) {
    return (
      <>
        <ReportHeader title="GL Ledger" sub="Choose a GL account and a date range within one year." />
        <Filters branch={branch} fields={fields}>{list}</Filters>
      </>
    );
  }
  return (
    <ReportPage title="GL Ledger" apiPath="gl-ledger" branch={branch} params={{ gl_code: gl, date_from: from, date_to: to }} fields={fields}>
      {list}
    </ReportPage>
  );
}
