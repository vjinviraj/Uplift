"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  FileText,
  Play,
  Receipt,
  ShoppingCart,
} from "lucide-react";

const navigation = [
  {
    label: "Checkout",
    href: "/",
    icon: ShoppingCart,
  },
  {
    label: "Overview",
    href: "/overview",
    icon: BarChart3,
  },
  {
    label: "Transactions",
    href: "/transactions",
    icon: Receipt,
  },
  {
    label: "Audit Log",
    href: "/audit",
    icon: FileText,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="hidden min-h-screen w-[220px] shrink-0 flex-col border-r border-zinc-800 bg-[#0F0F10] md:flex">
      <div className="px-[22px] pb-6 pt-5">
        <div className="flex items-center gap-2">
          <div className="h-5 w-5 rounded-md bg-gradient-to-br from-zinc-100 to-zinc-500" />

          <span className="text-base font-bold tracking-[-0.02em] text-zinc-100">
            UPLIFT
          </span>
        </div>
      </div>

      <div className="px-3">
        <div className="px-2 pb-1.5 pt-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
          Workspace
        </div>

        <nav className="space-y-0.5">
          {navigation.map((item) => {
            const Icon = item.icon;

            const active =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  "flex h-9 items-center gap-2.5 rounded-lg px-2.5",
                  "text-[13.5px] font-medium transition-colors",
                  active
                    ? "bg-[#18181B] text-zinc-100"
                    : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200",
                ].join(" ")}
              >
                <Icon className="h-4 w-4" strokeWidth={1.9} />
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="px-2 pb-1.5 pt-5 text-[11px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
          Demo
        </div>

        <button
          type="button"
          className="flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-[13.5px] font-medium text-zinc-500 transition-colors hover:bg-zinc-900 hover:text-zinc-200"
        >
          <Play className="h-4 w-4" strokeWidth={1.9} />
          Scenario Selector
        </button>
      </div>

      <div className="mt-auto px-5 pb-4">
        <div className="inline-flex items-center gap-1.5 rounded-md bg-[rgba(210,153,34,0.1)] px-2.5 py-1.5 text-[11px] font-semibold tracking-[0.04em] text-[#D29922]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#D29922]" />
          TEST MODE
        </div>
      </div>
    </aside>
  );
}