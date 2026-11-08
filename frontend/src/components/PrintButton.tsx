"use client";

export function PrintButton() {
  return (
    <button onClick={() => window.print()} className="rounded border px-3 py-1.5 text-sm hover:bg-gray-100">
      Print / PDF
    </button>
  );
}
