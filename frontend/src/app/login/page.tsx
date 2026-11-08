import { one, SP } from "@/lib/api";
import { LoginForm } from "./LoginForm";

export default async function LoginPage({ searchParams }: { searchParams: SP }) {
  const sp = await searchParams;
  return (
    <div className="mx-auto mt-16 max-w-sm rounded-lg border p-6 shadow-sm">
      <h1 className="text-xl font-bold">Sanasa Branch Reports</h1>
      <p className="mb-4 text-sm text-gray-500">Sign in to continue</p>
      {sp.expired && <p className="mb-3 text-sm text-amber-700">Your session has expired. Please sign in again.</p>}
      <LoginForm next={one(sp.next, "/")} />
    </div>
  );
}
