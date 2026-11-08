"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { api, API_URL } from "@/lib/api";
import { COOKIE } from "@/lib/session";

export type FormState = { error?: string; ok?: string };

export async function login(_: FormState, form: FormData): Promise<FormState> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
      cache: "no-store",
    });
  } catch {
    return { error: "Cannot reach the server. Is the backend running?" };
  }
  if (res.status === 401) return { error: "Invalid username or password" };
  if (!res.ok) return { error: `Login failed (${res.status})` };
  const { token } = await res.json();
  (await cookies()).set(COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.COOKIE_SECURE === "true",
    path: "/",
    maxAge: 60 * 60 * 8,
  });
  const next = String(form.get("next") || "/");
  redirect(next.startsWith("/") && !next.startsWith("//") ? next : "/");
}

export async function logout() {
  (await cookies()).delete(COOKIE);
  redirect("/login");
}

async function errorOf(res: Response | null): Promise<string> {
  if (!res) return "Cannot reach the server";
  try {
    const j = await res.json();
    return typeof j.detail === "string" ? j.detail : "Please check the fields (password min 8 characters)";
  } catch {
    return `Error ${res.status}`;
  }
}

export async function createUser(_: FormState, form: FormData): Promise<FormState> {
  const res = await api("/api/auth/users", {
    method: "POST",
    body: JSON.stringify({
      username: form.get("username"),
      fullName: form.get("fullName"),
      password: form.get("password"),
      role: form.get("role"),
      branch: form.get("branch"),
    }),
  });
  if (!res?.ok) return { error: await errorOf(res) };
  revalidatePath("/users");
  return { ok: `User ${form.get("username")} created` };
}

export async function updateUser(_: FormState, form: FormData): Promise<FormState> {
  const username = String(form.get("username"));
  const patch: Record<string, unknown> = {};
  if (form.has("active")) patch.active = form.get("active") === "true";
  if (form.get("password")) patch.password = form.get("password");
  if (form.get("role")) patch.role = form.get("role");
  if (form.get("branch")) patch.branch = form.get("branch");
  const res = await api(`/api/auth/users/${encodeURIComponent(username)}`, {
    method: "PATCH",
    body: JSON.stringify(patch),
  });
  if (!res?.ok) return { error: await errorOf(res) };
  revalidatePath("/users");
  return { ok: `${username} updated` };
}
