"use client";

import { useActionState, useRef } from "react";
import { createUser, FormState, updateUser } from "../actions";
import type { AppUser } from "./page";

const input = "rounded border px-2 py-1";

function Msg({ s }: { s: FormState }) {
  if (s.error) return <p className="text-xs text-red-600">{s.error}</p>;
  if (s.ok) return <p className="text-xs text-green-700">{s.ok}</p>;
  return null;
}

export function CreateUserForm() {
  const ref = useRef<HTMLFormElement>(null);
  const [state, action, pending] = useActionState(async (p: FormState, f: FormData) => {
    const r = await createUser(p, f);
    if (r.ok) ref.current?.reset();
    return r;
  }, {});
  return (
    <form ref={ref} action={action} className="mt-3 flex flex-wrap items-end gap-3 rounded-lg border p-3 text-sm">
      <label className="flex flex-col">Username<input name="username" required pattern="[A-Za-z0-9._\-]{3,50}" className={input} /></label>
      <label className="flex flex-col">Full name<input name="fullName" required className={input} /></label>
      <label className="flex flex-col">Password<input name="password" type="password" required minLength={8} autoComplete="new-password" className={input} /></label>
      <label className="flex flex-col">Role
        <select name="role" className={input}><option value="viewer">viewer</option><option value="admin">admin</option></select>
      </label>
      <label className="flex flex-col">Branch
        <select name="branch" className={input}>
          <option value="all">All</option><option value="001">Head Office</option><option value="002">Mahapitiya</option>
        </select>
      </label>
      <button disabled={pending} className="rounded bg-blue-700 px-4 py-1.5 text-white disabled:opacity-60">Create</button>
      <div className="w-full"><Msg s={state} /></div>
    </form>
  );
}

export function UserRowActions({ user, isSelf }: { user: AppUser; isSelf: boolean }) {
  const [state, action, pending] = useActionState(updateUser, {});
  return (
    <div className="flex flex-col gap-1">
      <form action={action} className="flex flex-wrap gap-1">
        <input type="hidden" name="username" value={user.username} />
        <select name="role" defaultValue={user.role} className={`${input} py-0.5 text-xs`} disabled={isSelf}>
          <option value="viewer">viewer</option><option value="admin">admin</option>
        </select>
        <select name="branch" defaultValue={user.branch} className={`${input} py-0.5 text-xs`}>
          <option value="all">All</option><option value="001">HO</option><option value="002">Mahapitiya</option>
        </select>
        <input name="password" type="password" placeholder="new password" minLength={8} autoComplete="new-password" className={`${input} w-32 py-0.5 text-xs`} />
        <button disabled={pending} className="rounded border px-2 text-xs hover:bg-gray-100">Save</button>
      </form>
      {!isSelf && (
        <form action={action}>
          <input type="hidden" name="username" value={user.username} />
          <input type="hidden" name="active" value={user.active ? "false" : "true"} />
          <button disabled={pending} className="text-xs text-blue-700 hover:underline">
            {user.active ? "Disable" : "Enable"}
          </button>
        </form>
      )}
      <Msg s={state} />
    </div>
  );
}
