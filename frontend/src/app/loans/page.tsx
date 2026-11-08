import { SP } from "@/lib/api";
import { branchFor } from "@/lib/session";
import { ReportPage } from "@/components/ui";

export default async function Loans({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  return <ReportPage title="Loan Portfolio" apiPath="loan-portfolio" branch={await branchFor(sp.branch)} params={{}} />;
}
