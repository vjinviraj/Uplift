"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BarChart3, CircleDollarSign, Receipt, TrendingUp } from "lucide-react";

import { AppShell } from "../../components/uplift/AppShell";
import { getOverview } from "../../lib/api";
import type { OverviewResponse } from "../../lib/types";

function formatMoney(paise: number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(paise / 100);
}

function formatStatus(status: string) {
  if (status === "PAID") return "PAID";
  if (status === "PAYMENT_FAILED" || status === "FAILED") return "FAILED";
  if (status === "ORDER_CREATED") return "ORDER CREATED";
  return status;
}

export default function OverviewPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void getOverview()
      .then(setData)
      .catch((err) =>
        setError(
          err instanceof Error ? err.message : "Unable to load overview.",
        ),
      );
  }, []);

  return (
    <AppShell title="Merchant Overview">
      <div className="mx-auto max-w-[1240px] p-5 md:p-7">
        <div className="mb-6">
          <h1 className="text-[26px] font-bold tracking-[-0.02em]">
            Merchant Overview
          </h1>
          <p className="mt-1 text-[13.5px] text-zinc-400">
            Live merchant value from the current Uplift transaction data.
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-950 bg-red-950/20 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            icon={<Receipt className="h-4 w-4" />}
            label="Sessions"
            value={data ? String(data.sessions) : "—"}
          />

          <MetricCard
            icon={<CircleDollarSign className="h-4 w-4" />}
            label="Revenue"
            value={data ? formatMoney(data.revenue_paise) : "—"}
          />

          <MetricCard
            icon={<BarChart3 className="h-4 w-4" />}
            label="AOV"
            value={data ? formatMoney(data.aov_paise) : "—"}
          />

          <MetricCard
            icon={<TrendingUp className="h-4 w-4" />}
            label="Upsell acceptance"
            value={data ? `${data.upsell_acceptance_pct}%` : "—"}
          />
        </div>

        <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_330px]">
          <section className="rounded-xl border border-zinc-800 bg-[#0F0F10]">
            <div className="border-b border-zinc-800 px-4 py-3">
              <div className="text-sm font-semibold">Recent Transactions</div>
              <div className="mt-0.5 text-[11px] text-zinc-600">
                Newest orders from the backend database
              </div>
            </div>

            <div className="divide-y divide-zinc-900">
              {data?.recent_transactions.length ? (
                data.recent_transactions.map((tx) => (
                  <Link
                    key={tx.local_order_id}
                    href={`/transactions/${encodeURIComponent(tx.session_id)}`}
                    className="flex items-center justify-between gap-4 px-4 py-3.5 transition hover:bg-[#18181B]"
                  >
                    <div className="min-w-0">
                      <div className="truncate text-[13.5px] font-medium text-zinc-200">
                        {tx.product_name}
                      </div>

                      <div className="mt-0.5 font-mono text-[10.5px] text-zinc-600">
                        #{tx.local_order_id} ·{" "}
                        {tx.razorpay_order_id ?? "No Razorpay order"}
                      </div>
                    </div>

                    <div className="shrink-0 text-right">
                      <div className="text-[13.5px] font-semibold tabular-nums">
                        {formatMoney(tx.amount_paise, tx.currency)}
                      </div>

                      <div
                        className={
                          tx.status === "PAID"
                            ? "text-[10.5px] font-semibold text-[#3FB950]"
                            : "text-[10.5px] font-semibold text-[#D29922]"
                        }
                      >
                        {formatStatus(tx.status)}
                      </div>
                    </div>
                  </Link>
                ))
              ) : (
                <div className="px-4 py-12 text-center text-sm text-zinc-600">
                  No transactions recorded yet.
                </div>
              )}
            </div>
          </section>

          <section className="rounded-xl border border-zinc-800 bg-[#0F0F10]">
            <div className="border-b border-zinc-800 px-4 py-3">
              <div className="text-sm font-semibold">Upsell Impact</div>
              <div className="mt-0.5 text-[11px] text-zinc-600">
                Measurement status
              </div>
            </div>

            <div className="space-y-4 px-4 py-5">
              <div>
                <div className="text-[11px] uppercase tracking-[0.06em] text-zinc-600">
                  Upsell orders
                </div>
                <div className="mt-1 text-xl font-bold tabular-nums">
                  {data ? data.upsell_orders : "—"}
                </div>
              </div>

              <div>
                <div className="text-[11px] uppercase tracking-[0.06em] text-zinc-600">
                  Paid orders
                </div>
                <div className="mt-1 text-xl font-bold tabular-nums">
                  {data ? data.paid_orders : "—"}
                </div>
              </div>

              <div className="rounded-lg border border-zinc-800 bg-[#18181B] p-3">
                <div className="text-[11px] uppercase tracking-[0.06em] text-zinc-600">
                  AOV lift
                </div>

                <div className="mt-1 text-sm font-semibold text-zinc-300">
                  Not measured yet
                </div>

                <div className="mt-1 text-[11px] leading-5 text-zinc-600">
                  Control vs treatment measurement belongs to the later
                  measurement phase. No fabricated revenue impact is shown here.
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </AppShell>
  );
}

function MetricCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-[#0F0F10] px-4 py-4">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
        {icon}
        {label}
      </div>

      <div className="mt-2 text-[24px] font-bold tracking-[-0.02em] tabular-nums">
        {value}
      </div>
    </div>
  );
}