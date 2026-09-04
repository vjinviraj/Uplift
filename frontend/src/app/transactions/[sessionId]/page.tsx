"use client";

import { useEffect, useState } from "react";
import {
  ArrowLeft,
  CheckCircle2,
  CircleDollarSign,
  Clock3,
  FileText,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { AppShell } from "../../../components/uplift/AppShell";
import { getTransaction } from "../../../lib/api";
import type { TransactionResponse } from "../../../lib/types";

function formatMoney(
  paise: number,
  currency = "INR",
) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(paise / 100);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function statusClass(status: string) {
  if (status === "PAID") {
    return "text-[#3FB950]";
  }

  if (
    status === "PAYMENT_FAILED" ||
    status === "FAILED" ||
    status === "REJECTED"
  ) {
    return "text-[#F85149]";
  }

  return "text-[#D29922]";
}

export default function TransactionDetailPage() {
  const params = useParams<{ sessionId: string }>();
  const sessionId = params.sessionId;

  const [data, setData] = useState<TransactionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    void getTransaction(sessionId)
      .then(setData)
      .catch((err) =>
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load transaction.",
        ),
      );
  }, [sessionId]);

  return (
    <AppShell title="Transaction Detail">
      <div className="mx-auto max-w-[1240px] p-5 md:p-7">
        <div className="mb-5">
          <Link
            href="/overview"
            className="inline-flex items-center gap-1.5 text-[12px] text-zinc-500 transition hover:text-zinc-300"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to Overview
          </Link>

          <div className="mt-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-zinc-600">
                Transaction
              </div>

              <h1 className="mt-1 text-[26px] font-bold tracking-[-0.02em]">
                {data?.offer.breakdown[0]?.name ??
                  "Transaction Detail"}
              </h1>

              <div className="mt-1 font-mono text-[10.5px] text-zinc-600">
                {sessionId}
              </div>
            </div>

            {data && (
              <div
                className={`text-sm font-semibold ${statusClass(
                  data.status,
                )}`}
              >
                {data.status}
              </div>
            )}
          </div>
        </div>

        {error && (
          <div className="rounded-xl border border-red-950 bg-red-950/20 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        {!data && !error && (
          <div className="rounded-xl border border-zinc-800 bg-[#0F0F10] px-4 py-16 text-center text-sm text-zinc-600">
            Loading transaction…
          </div>
        )}

        {data && (
          <>
            <div className="grid gap-3 md:grid-cols-3">
              <SummaryCard
                icon={<CircleDollarSign className="h-4 w-4" />}
                label="Order amount"
                value={formatMoney(
                  data.amount_paise,
                  data.currency,
                )}
              />

              <SummaryCard
                icon={<ShieldCheck className="h-4 w-4" />}
                label="Authorization"
                value={data.authorization_status}
              />

              <SummaryCard
                icon={<FileText className="h-4 w-4" />}
                label="Razorpay order"
                value={
                  data.razorpay_order_id ?? "Not created"
                }
              />
            </div>

            <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
              <div className="space-y-5">
                <section className="rounded-xl border border-zinc-800 bg-[#0F0F10]">
                  <SectionHeader
                    title="Buyer Request"
                    subtitle="Persisted purchase intent"
                  />

                  <div className="space-y-4 px-4 py-4">
                    <div>
                      <Label>Query</Label>
                      <div className="mt-1 text-sm text-zinc-200">
                        {data.request.query}
                      </div>
                    </div>

                    <div className="grid gap-4 sm:grid-cols-2">
                      <div>
                        <Label>Budget</Label>
                        <div className="mt-1 text-sm text-zinc-200">
                          {data.request.budget_paise === null
                            ? "No budget"
                            : formatMoney(
                                data.request.budget_paise,
                              )}
                        </div>
                      </div>

                      <div>
                        <Label>Category</Label>
                        <div className="mt-1 text-sm text-zinc-200">
                          {data.request.category_hint ??
                            "Not specified"}
                        </div>
                      </div>

                      <div>
                        <Label>Platform</Label>
                        <div className="mt-1 text-sm text-zinc-200">
                          {data.request.platform_hint ??
                            "Not specified"}
                        </div>
                      </div>

                      <div>
                        <Label>Franchise</Label>
                        <div className="mt-1 text-sm text-zinc-200">
                          {data.request.franchise_hint ??
                            "Not specified"}
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                <section className="rounded-xl border border-zinc-800 bg-[#0F0F10]">
                  <SectionHeader
                    title="Merchant Proposal"
                    subtitle="Server-returned offer"
                  />

                  <div className="divide-y divide-zinc-900">
                    {data.offer.breakdown.map((item) => (
                      <div
                        key={`${item.product_id}-${item.qty}`}
                        className="flex items-center justify-between gap-4 px-4 py-3.5"
                      >
                        <div>
                          <div className="text-sm font-medium text-zinc-200">
                            {item.name}
                          </div>

                          <div className="mt-0.5 font-mono text-[10px] text-zinc-600">
                            {item.product_id} · qty {item.qty}
                          </div>
                        </div>

                        <div className="text-right">
                          <div className="text-sm font-semibold tabular-nums">
                            {formatMoney(
                              item.line_total_paise,
                              data.offer.currency,
                            )}
                          </div>

                          <div className="text-[10px] text-zinc-600">
                            {formatMoney(
                              item.unit_price_paise,
                              data.offer.currency,
                            )}{" "}
                            each
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {data.offer.upsell_product_id && (
                    <div className="border-t border-zinc-800 px-4 py-4">
                      <Label>Upsell reason</Label>
                      <div className="mt-1 text-sm leading-6 text-zinc-300">
                        {data.offer.upsell_reason ??
                          "No reason provided"}
                      </div>
                    </div>
                  )}
                </section>

                <section className="rounded-xl border border-zinc-800 bg-[#0F0F10]">
                  <SectionHeader
                    title="Policy & Approval"
                    subtitle="Authorization evidence"
                  />

                  <div className="grid gap-4 px-4 py-4 sm:grid-cols-2">
                    <Evidence
                      label="Policy"
                      value={data.offer.policy_decision}
                    />

                    <Evidence
                      label="Policy reason"
                      value={data.offer.policy_reason}
                    />

                    <Evidence
                      label="Policy version"
                      value={data.offer.policy_version}
                    />

                    <Evidence
                      label="Buyer approval"
                      value={
                        data.buyer_approval_recorded
                          ? `Exact amount: ${formatMoney(
                              data.buyer_approval_amount_paise ??
                                data.amount_paise,
                              data.currency,
                            )}`
                          : "No persisted approval record"
                      }
                      muted={!data.buyer_approval_recorded}
                    />
                  </div>

                  {!data.buyer_approval_recorded && (
                    <div className="border-t border-zinc-800 px-4 py-3 text-[11px] leading-5 text-zinc-600">
                      The current backend does not have a dedicated
                      buyer-approval table. This screen therefore does
                      not claim a durable approval record where one does
                      not exist.
                    </div>
                  )}
                </section>

                <section className="rounded-xl border border-zinc-800 bg-[#0F0F10]">
                  <SectionHeader
                    title="Payment"
                    subtitle="Razorpay and reconciliation state"
                  />

                  <div className="px-4 py-4">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <Evidence
                        label="Local order"
                        value={
                          data.order_id === null
                            ? "Not created"
                            : `#${data.order_id}`
                        }
                      />

                      <Evidence
                        label="Order status"
                        value={
                          data.order_status ?? "Not created"
                        }
                      />

                      <Evidence
                        label="Razorpay order"
                        value={
                          data.razorpay_order_id ??
                          "Not created"
                        }
                      />

                      <Evidence
                        label="Payments"
                        value={`${data.payments.length}`}
                      />
                    </div>

                    <div className="mt-4 space-y-2">
                      {data.payments.map((payment) => (
                        <div
                          key={payment.id}
                          className="rounded-lg border border-zinc-800 bg-[#18181B] px-3 py-3"
                        >
                          <div className="flex items-center justify-between gap-3">
                            <div>
                              <div className="font-mono text-[11px] text-zinc-300">
                                {payment.razorpay_payment_id}
                              </div>

                              <div className="mt-1 text-[11px] text-zinc-600">
                                {payment.method}
                                {payment.verified_at
                                  ? ` · verified ${formatDate(
                                      payment.verified_at,
                                    )}`
                                  : ""}
                              </div>
                            </div>

                            <div
                              className={`text-[10.5px] font-semibold ${statusClass(
                                payment.status,
                              )}`}
                            >
                              {payment.status}
                            </div>
                          </div>

                          {payment.failure_reason && (
                            <div className="mt-2 text-[11px] text-red-300">
                              {payment.failure_reason}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </section>
              </div>

              <section className="h-fit rounded-xl border border-zinc-800 bg-[#0F0F10]">
                <SectionHeader
                  title="Audit Timeline"
                  subtitle="Append-only backend events"
                />

                <div className="px-4 py-4">
                  {data.audit_events.length === 0 ? (
                    <div className="py-8 text-center text-sm text-zinc-600">
                      No audit events recorded.
                    </div>
                  ) : (
                    <div className="space-y-0">
                      {data.audit_events.map((event, index) => {
                        const failed =
                          event.decision === "REJECTED" ||
                          event.event_type.includes("failed");

                        const complete =
                          event.decision === "ALLOWED" ||
                          event.event_type.includes(
                            "success",
                          ) ||
                          event.event_type.includes(
                            "created",
                          );

                        return (
                          <div
                            key={event.id}
                            className="relative pl-8"
                          >
                            {index <
                              data.audit_events.length - 1 && (
                              <div className="absolute bottom-0 left-[7px] top-5 w-px bg-zinc-800" />
                            )}

                            <div className="absolute left-0 top-0.5">
                              {failed ? (
                                <XCircle className="h-4 w-4 text-[#F85149]" />
                              ) : complete ? (
                                <CheckCircle2 className="h-4 w-4 text-[#3FB950]" />
                              ) : (
                                <Clock3 className="h-4 w-4 text-[#D29922]" />
                              )}
                            </div>

                            <div className="pb-5">
                              <div className="text-[12px] font-semibold text-zinc-200">
                                {event.event_type}
                              </div>

                              <div className="mt-0.5 text-[10px] text-zinc-600">
                                {event.actor_type} ·{" "}
                                {event.action_id}
                              </div>

                              <div className="mt-1 text-[10px] text-zinc-700">
                                {formatDate(event.timestamp)}
                              </div>

                              {event.decision && (
                                <div className="mt-2 text-[11px] text-zinc-400">
                                  Decision: {event.decision}
                                </div>
                              )}

                              {event.reason && (
                                <div className="mt-1 text-[11px] leading-5 text-zinc-500">
                                  {event.reason}
                                </div>
                              )}

                              {event.policy_version && (
                                <div className="mt-1 font-mono text-[10px] text-zinc-700">
                                  policy {event.policy_version}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </section>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}

function SectionHeader({
  title,
  subtitle,
}: {
  title: string;
  subtitle: string;
}) {
  return (
    <div className="border-b border-zinc-800 px-4 py-3">
      <div className="text-sm font-semibold">{title}</div>
      <div className="mt-0.5 text-[11px] text-zinc-600">
        {subtitle}
      </div>
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
      {children}
    </div>
  );
}

function Evidence({
  label,
  value,
  muted = false,
}: {
  label: string;
  value: string;
  muted?: boolean;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div
        className={`mt-1 text-sm ${
          muted ? "text-zinc-600" : "text-zinc-200"
        }`}
      >
        {value}
      </div>
    </div>
  );
}

function SummaryCard({
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

      <div className="mt-2 truncate text-[18px] font-bold tracking-[-0.01em]">
        {value}
      </div>
    </div>
  );
}