const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Branch = { code: string; name: string };
type Health = { status: string; databases?: Record<string, string>; error?: string };

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_URL}${path}`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

export default async function Home() {
  const [health, branches] = await Promise.all([
    getJson<Health>("/api/health"),
    getJson<Branch[]>("/api/branches"),
  ]);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-bold">Sanasa – Consolidated Branch Reports</h1>
      <p className="mt-1 text-sm text-gray-500">
        Read-only reporting over MicroBanker branch databases
      </p>

      <section className="mt-8 rounded-lg border p-4">
        <h2 className="font-semibold">Backend status</h2>
        <p className="mt-2">
          API:{" "}
          <span className={health?.status === "ok" ? "text-green-600" : "text-red-600"}>
            {health ? health.status : "unreachable"}
          </span>
        </p>
        {health?.error && <p className="text-sm text-red-600">{health.error}</p>}
      </section>

      <section className="mt-6 rounded-lg border p-4">
        <h2 className="font-semibold">Branches</h2>
        <ul className="mt-2 space-y-1">
          {(branches ?? []).map((b) => (
            <li key={b.code} className="flex justify-between">
              <span>
                {b.code} – {b.name}
              </span>
              <span className="text-sm text-gray-500">
                DB: {health?.databases?.[b.code] ?? "?"}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
