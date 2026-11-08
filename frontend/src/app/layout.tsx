import type { Metadata } from "next";
import Link from "next/link";
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

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">
        <nav className="no-print border-b bg-blue-900 text-white">
          <div className="mx-auto flex max-w-6xl flex-wrap gap-4 px-4 py-3 text-sm">
            <span className="font-bold">Sanasa Reports</span>
            {NAV.map(([href, label]) => (
              <Link key={href} href={href} className="hover:underline">
                {label}
              </Link>
            ))}
          </div>
        </nav>
        <main className="mx-auto max-w-6xl p-4 md:p-8">{children}</main>
      </body>
    </html>
  );
}
