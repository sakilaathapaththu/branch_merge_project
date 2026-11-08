import { SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { ReportPage } from "@/components/ui";

export default async function Deposits({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  return <ReportPage title="Deposits" apiPath="deposits" branch={await branchFor(sp.branch)} params={{}} />;
}
