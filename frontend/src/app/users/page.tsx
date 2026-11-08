import { redirect } from "next/navigation";
import { getJson } from "@/lib/api";
import { getUser } from "@/lib/session";
import { CreateUserForm, UserRowActions } from "./forms";

export type AppUser = {
  username: string;
  fullName: string;
  role: "admin" | "viewer";
  branch: "all" | "001" | "002";
  active: boolean;
  createdAt: string | null;
  lastLoginAt: string | null;
};

const BRANCH: Record<string, string> = { all: "All", "001": "Head Office", "002": "Mahapitiya" };

export default async function UsersPage() {
  const me = await getUser();
  if (me?.role !== "admin") redirect("/");
  const users = (await getJson<AppUser[]>("/api/auth/users")) ?? [];

  return (
    <>
      <h1 className="text-2xl font-bold">Users</h1>
      <p className="text-sm text-gray-500">
        Admins manage users and see all branches. Viewers see reports for their branch only.
      </p>

      <table className="mt-6 w-full text-sm">
        <thead>
          <tr className="border-b-2 text-left">
            <th className="py-1">Username</th><th>Name</th><th>Role</th><th>Branch</th><th>Status</th><th>Last login</th><th></th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.username} className="border-b align-top">
              <td className="py-1.5 font-mono">{u.username}</td>
              <td>{u.fullName}</td>
              <td>{u.role}</td>
              <td>{BRANCH[u.branch]}</td>
              <td className={u.active ? "text-green-700" : "text-red-700"}>{u.active ? "Active" : "Disabled"}</td>
              <td className="whitespace-nowrap">{u.lastLoginAt?.replace("T", " ") ?? "never"}</td>
              <td><UserRowActions user={u} isSelf={u.username === me.username} /></td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 className="mt-10 text-lg font-semibold">Add user</h2>
      <CreateUserForm />
    </>
  );
}
