"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { BarChart3, FileText, Play, Receipt, ShoppingCart } from "lucide-react";

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
        <div className="flex items-center">
          <div className="flex items-center">
            <Image
              src="/brand/uplift-logo.png"
              alt="Uplift"
              width={120}
              height={40}
              className="h-auto w-[100px] sm:w-[120px] md:w-[140px]" // Different sizes per breakpoint
              priority
            />
          </div>
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

        <Link
          href="/scenario"
          className={[
            "flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5",
            "text-[13.5px] font-medium transition-colors",
            pathname.startsWith("/scenario")
              ? "bg-[#18181B] text-zinc-100"
              : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200",
          ].join(" ")}
        >
          <Play className="h-4 w-4" strokeWidth={1.9} />
          Scenario Selector
        </Link>
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
