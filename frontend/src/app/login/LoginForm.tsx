"use client";

import { useActionState } from "react";
import { login } from "../actions";

export function LoginForm({ next }: { next: string }) {
  const [state, action, pending] = useActionState(login, {});
  return (
    <form action={action} className="flex flex-col gap-3 text-sm">
      <input type="hidden" name="next" value={next} />
      <label className="flex flex-col">
        Username
        <input name="username" required autoFocus autoComplete="username" className="rounded border px-2 py-1.5" />
      </label>
      <label className="flex flex-col">
        Password
        <input name="password" type="password" required autoComplete="current-password" className="rounded border px-2 py-1.5" />
      </label>
      {state.error && <p className="text-red-600">{state.error}</p>}
      <button disabled={pending} className="rounded bg-blue-700 py-2 text-white disabled:opacity-60">
        {pending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
