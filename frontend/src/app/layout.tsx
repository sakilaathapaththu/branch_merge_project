import type { Metadata } from "next";
import Link from "next/link";
import { getUser } from "@/lib/session";
import { logout } from "./actions";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sanasa Branch Reports",
  description: "Consolidated read-only reporting over MicroBanker branch databases",
};

const NAV = [
  ["/", "Dashboard"],
  ["/trial-balance", "Trial Balance"],
  ["/balance-sheet", "Balance Sheet"],
  ["/profit-loss", "Profit & Loss"],
  ["/transactions", "Transactions"],
];

const BRANCH_LABEL: Record<string, string> = { all: "All branches", "001": "Head Office", "002": "Mahapitiya" };

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const user = await getUser();
  return (
    <html lang="en">
      <body className="antialiased">
        {user && (
          <nav className="no-print border-b bg-blue-900 text-white">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-3 text-sm">
              <span className="font-bold">Sanasa Reports</span>
              {NAV.map(([href, label]) => (
                <Link key={href} href={href} className="hover:underline">
                  {label}
                </Link>
              ))}
              {user.role === "admin" && (
                <Link href="/users" className="hover:underline">
                  Users
                </Link>
              )}
              <span className="ml-auto text-blue-200">
                {user.fullName} · {user.role} · {BRANCH_LABEL[user.branch]}
              </span>
              <form action={logout}>
                <button className="rounded border border-blue-300 px-2 py-0.5 hover:bg-blue-800">Logout</button>
              </form>
            </div>
          </nav>
        )}
        <main className="mx-auto max-w-6xl p-4 md:p-8">{children}</main>
      </body>
    </html>
  );
}
