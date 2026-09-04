"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CircleAlert,
  Clock3,
  FileText,
} from "lucide-react";

import { AppShell } from "@/components/uplift/AppShell";
import { getAuditLog } from "@/lib/api";
import type { AuditLogEvent } from "@/lib/types";

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-IN", {
    dateStyle: "medium",
    timeStyle: "medium",
  }).format(new Date(value));
}

function formatMoney(paise: number | null) {
  if (paise === null) {
    return "—";
  }

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(paise / 100);
}

function eventIcon(event: AuditLogEvent) {
  if (
    event.decision === "REJECTED" ||
    event.event_type.includes("failed")
  ) {
    return <CircleAlert className="h-4 w-4 text-[#F85149]" />;
  }

  if (
    event.decision === "ALLOWED" ||
    event.event_type.includes("success") ||
    event.event_type.includes("created") ||
    event.event_type.includes("approved")
  ) {
    return <CheckCircle2 className="h-4 w-4 text-[#3FB950]" />;
  }

  return <Clock3 className="h-4 w-4 text-[#D29922]" />;
}

function decisionClass(decision: string | null) {
  if (decision === "ALLOWED") {
    return "text-[#3FB950]";
  }

  if (decision === "REJECTED") {
    return "text-[#F85149]";
  }

  return "text-zinc-400";
}

export default function AuditLogPage() {
  const [events, setEvents] = useState<AuditLogEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    void getAuditLog()
      .then((response) => setEvents(response.events))
      .catch((err) => {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load audit log.",
        );
      });
  }, []);

  return (
    <AppShell title="Audit Log">
      <div className="mx-auto max-w-[1240px] p-5 md:p-7">
        <div className="mb-6">
          <h1 className="text-[26px] font-bold tracking-[-0.02em]">
            Audit Log
          </h1>

          <p className="mt-1 text-[13.5px] text-zinc-400">
            Append-only record of Uplift decisions and payment workflow
            events.
          </p>
        </div>

        {error && (
          <div className="mb-4 rounded-xl border border-red-950 bg-red-950/20 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <section className="overflow-hidden rounded-xl border border-zinc-800 bg-[#0F0F10]">
          <div className="grid grid-cols-[1.55fr_110px_120px_150px_1.2fr_90px] gap-3 border-b border-zinc-800 px-4 py-3 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
            <div>Event</div>
            <div>Actor</div>
            <div>Decision</div>
            <div>Time</div>
            <div>Session</div>
            <div className="text-right">Detail</div>
          </div>

          {events.length === 0 ? (
            <div className="px-4 py-16 text-center text-sm text-zinc-600">
              No audit events recorded yet.
            </div>
          ) : (
            <div className="divide-y divide-zinc-900">
              {events.map((event) => {
                const expanded = expandedId === event.id;

                return (
                  <div key={event.id}>
                    <button
                      type="button"
                      onClick={() =>
                        setExpandedId(
                          expanded ? null : event.id,
                        )
                      }
                      className="grid w-full grid-cols-[1.55fr_110px_120px_150px_1.2fr_90px] items-center gap-3 px-4 py-3.5 text-left transition hover:bg-[#18181B]"
                    >
                      <div className="flex min-w-0 items-center gap-2.5">
                        {eventIcon(event)}

                        <div className="min-w-0">
                          <div className="truncate text-[13px] font-medium text-zinc-200">
                            {event.event_type}
                          </div>

                          <div className="mt-0.5 truncate font-mono text-[10px] text-zinc-600">
                            {event.action_id}
                          </div>
                        </div>
                      </div>

                      <div className="truncate text-[11px] text-zinc-400">
                        {event.actor_type}
                      </div>

                      <div
                        className={`truncate text-[11px] font-semibold ${decisionClass(
                          event.decision,
                        )}`}
                      >
                        {event.decision ?? "—"}
                      </div>

                      <div className="text-[10.5px] text-zinc-600">
                        {formatDate(event.timestamp)}
                      </div>

                      <div className="min-w-0">
                        <Link
                          href={`/transactions/${encodeURIComponent(
                            event.session_id,
                          )}`}
                          onClick={(e) => e.stopPropagation()}
                          className="block truncate font-mono text-[10.5px] text-zinc-500 transition hover:text-zinc-200"
                        >
                          {event.session_id}
                        </Link>
                      </div>

                      <div className="flex justify-end text-zinc-600">
                        {expanded ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </div>
                    </button>

                    {expanded && (
                      <div className="border-t border-zinc-900 bg-[#0C0C0E] px-4 py-4">
                        <div className="grid gap-5 lg:grid-cols-2">
                          <div>
                            <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.06em] text-zinc-500">
                              <FileText className="h-3.5 w-3.5" />
                              Event Details
                            </div>

                            <div className="grid gap-3 sm:grid-cols-2">
                              <Detail
                                label="Event ID"
                                value={`#${event.id}`}
                              />

                              <Detail
                                label="Action"
                                value={event.action_id}
                              />

                              <Detail
                                label="Policy"
                                value={
                                  event.policy_version ??
                                  "—"
                                }
                              />

                              <Detail
                                label="Buyer budget"
                                value={formatMoney(
                                  event.buyer_budget_paise,
                                )}
                              />

                              <Detail
                                label="Razorpay order"
                                value={
                                  event.razorpay_order_id ??
                                  "—"
                                }
                              />

                              <Detail
                                label="Razorpay payment"
                                value={
                                  event.razorpay_payment_id ??
                                  "—"
                                }
                              />
                            </div>

                            {event.reason && (
                              <div className="mt-4">
                                <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
                                  Reason
                                </div>

                                <div className="mt-1 text-[12px] leading-5 text-zinc-400">
                                  {event.reason}
                                </div>
                              </div>
                            )}
                          </div>

                          <div>
                            <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.06em] text-zinc-500">
                              Payload
                            </div>

                            <pre className="max-h-[280px] overflow-auto rounded-lg border border-zinc-800 bg-[#18181B] p-3 font-mono text-[10px] leading-5 text-zinc-500">
                              {JSON.stringify(
                                event.payload,
                                null,
                                2,
                              )}
                            </pre>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>
    </AppShell>
  );
}

function Detail({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
        {label}
      </div>

      <div className="mt-1 break-all font-mono text-[11px] text-zinc-300">
        {value}
      </div>
    </div>
  );
}