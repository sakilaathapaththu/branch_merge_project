import Link from "next/link";
import { getJson, money, one, SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { Filters, ReportHeader, Unavailable } from "@/components/ui";

type Trn = {
  page: number;
  size: number;
  total: number;
  items: { id: string; branch: string; date: string; acc: string; trnType: string; description: string; amount: number; balance: number; cid: string; teller: string }[];
};

export default async function Transactions({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  const branch = await branchFor(sp.branch);
  const from = one(sp.from, "");
  const to = one(sp.to, "");
  const acc = one(sp.acc, "");
  const page = Number(one(sp.page, "1")) || 1;
  const params = new URLSearchParams({ branch, page: String(page), size: "50" });
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  if (acc) params.set("acc", acc);
  const data = await getJson<Trn>(`/api/transactions?${params}`);
  const pages = data ? Math.max(1, Math.ceil(data.total / data.size)) : 1;
  const link = (p: number) => {
    const s = new URLSearchParams(params);
    s.set("page", String(p));
    s.delete("size");
    return `/transactions?${s}`;
  };

  return (
    <>
      <ReportHeader title="Transactions" sub="Posted transaction history (T_TRNHIST) · LKR" />
      <Filters
        branch={branch}
        dates={[
          { name: "from", label: "From", value: from },
          { name: "to", label: "To", value: to },
        ]}
        extra={
          <label className="flex flex-col">
            Account no.
            <input name="acc" defaultValue={acc} className="rounded border px-2 py-1" />
          </label>
        }
      />
      {!data ? (
        <Unavailable />
      ) : (
        <>
          <p className="mt-3 text-sm text-gray-500">{data.total.toLocaleString()} transactions · page {page} of {pages}</p>
          <table className="mt-2 w-full text-sm">
            <thead>
              <tr className="border-b-2 text-left">
                <th className="py-1">Branch</th><th>Date</th><th>Account</th><th>Type</th><th>Description</th>
                <th className="text-right">Amount</th><th className="text-right">Balance</th><th>CID</th><th>Teller</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((t) => (
                <tr key={t.id} className="border-b border-gray-100">
                  <td className="py-0.5">{t.branch}</td>
                  <td className="whitespace-nowrap">{t.date}</td>
                  <td className="font-mono text-xs">{t.acc}</td>
                  <td>{t.trnType}</td>
                  <td>{t.description}</td>
                  <td className="text-right tabular-nums">{money(t.amount)}</td>
                  <td className="text-right tabular-nums">{money(t.balance)}</td>
                  <td>{t.cid}</td>
                  <td>{t.teller}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="no-print mt-4 flex gap-3 text-sm">
            {page > 1 && <Link href={link(page - 1)} className="text-blue-700 hover:underline">← Previous</Link>}
            {page < pages && <Link href={link(page + 1)} className="text-blue-700 hover:underline">Next →</Link>}
          </div>
        </>
      )}
    </>
  );
}
