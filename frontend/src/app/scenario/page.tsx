"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Check, ChevronRight, Play } from "lucide-react";

import { AppShell } from "@/components/uplift/AppShell";
import { getExperimentSummary } from "@/lib/api";
import type { ExperimentSummaryResponse } from "@/lib/types";
import {
  DEMO_SCENARIOS,
  type ScenarioId,
} from "@/lib/scenarios";

export default function ScenarioSelectorPage() {
  return (
    <AppShell title="Scenario Selector">
      <div className="mx-auto max-w-[980px] p-5 md:p-7">
        <div className="mb-6">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-zinc-600">
            Demo controls
          </div>

          <h1 className="mt-1 text-[26px] font-bold tracking-[-0.02em]">
            Scenario Selector
          </h1>

          <p className="mt-1 max-w-2xl text-[13.5px] leading-6 text-zinc-400">
            Choose a controlled buyer request. Uplift will send the request
            through the normal backend workflow; pricing, policy, authorization
            and payment truth remain server-side.
          </p>
        </div>

        <div className="grid gap-3">
          {DEMO_SCENARIOS.map((scenario) => (
            <ScenarioCard
              key={scenario.id}
              scenarioId={scenario.id}
              name={scenario.name}
              description={scenario.description}
            />
          ))}
        </div>

        <ExperimentPanel />

        <div className="mt-5 rounded-xl border border-zinc-800 bg-[#0F0F10] px-4 py-4">
          <div className="text-[11px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
            Safety boundary
          </div>

          <div className="mt-2 space-y-2">
            <SafetyItem>
              Scenario selection changes request inputs only.
            </SafetyItem>

            <SafetyItem>
              Server determines the offer and authoritative amount.
            </SafetyItem>

            <SafetyItem>
              Policy rejection still stops authorization.
            </SafetyItem>

            <SafetyItem>
              The browser never marks a payment as successful by itself.
            </SafetyItem>
          </div>
        </div>
      </div>
    </AppShell>
  );
}

function ScenarioCard({
  scenarioId,
  name,
  description,
}: {
  scenarioId: ScenarioId;
  name: string;
  description: string;
}) {
  return (
    <Link
      href={`/?scenario=${encodeURIComponent(scenarioId)}`}
      className="group flex items-center justify-between gap-4 rounded-xl border border-zinc-800 bg-[#0F0F10] px-4 py-4 transition hover:border-zinc-700 hover:bg-[#18181B]"
    >
      <div className="flex min-w-0 items-start gap-3">
        <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-[#18181B] text-zinc-500">
          <Play className="h-3.5 w-3.5" />
        </div>

        <div className="min-w-0">
          <div className="text-sm font-semibold text-zinc-200">
            {name}
          </div>

          <div className="mt-1 text-[12px] leading-5 text-zinc-600">
            {description}
          </div>
        </div>
      </div>

      <ChevronRight className="h-4 w-4 shrink-0 text-zinc-700 transition group-hover:text-zinc-400" />
    </Link>
  );
}

function SafetyItem({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-zinc-400">
      <Check className="h-3.5 w-3.5 shrink-0 text-[#3FB950]" />
      {children}
    </div>
  );
}

function ExperimentPanel() {
  const [summary, setSummary] = useState<ExperimentSummaryResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    getExperimentSummary()
      .then((result) => {
        if (!cancelled) {
          setSummary(result);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setSummary(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const money = (paise: number) =>
    new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0,
    }).format(paise / 100);

  return (
    <div className="mt-5 rounded-xl border border-zinc-800 bg-[#0F0F10] px-4 py-4">
      <div className="text-[11px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
        Revenue experiment
      </div>
      <div className="mt-1 text-sm font-semibold text-zinc-200">
        Measured Test Mode outcomes
      </div>

      {summary ? (
        <>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <MetricColumn
              title="Control · no upsell"
              metrics={summary.control}
              money={money}
            />
            <MetricColumn
              title="Treatment · upsell"
              metrics={summary.treatment}
              money={money}
            />
          </div>

          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            <Metric label="AOV lift" value={
              summary.aov_lift_pct === null ? "—" : `${summary.aov_lift_pct}%`
            } />
            <Metric
              label="Upsell acceptance"
              value={`${summary.upsell_acceptance_pct}%`}
            />
            <Metric
              label="Blocked unsafe actions"
              value={String(summary.blocked_unsafe_actions)}
            />
          </div>

          <div className="mt-3 rounded-lg border border-zinc-800 bg-[#18181B] px-3 py-3 text-[11px] leading-5 text-zinc-500">
            {summary.methodology}
          </div>
        </>
      ) : (
        <div className="mt-3 text-[12px] text-zinc-600">
          No measurement data available yet.
        </div>
      )}
    </div>
  );
}

function MetricColumn({
  title,
  metrics,
  money,
}: {
  title: string;
  metrics: {
    sessions: number;
    successful_orders: number;
    revenue_paise: number;
    aov_paise: number;
    conversion_pct: number;
  };
  money: (paise: number) => string;
}) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-[#18181B] px-3 py-3">
      <div className="text-[11px] font-semibold uppercase tracking-[0.05em] text-zinc-500">
        {title}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <Metric label="Sessions" value={String(metrics.sessions)} />
        <Metric label="Paid" value={String(metrics.successful_orders)} />
        <Metric label="Revenue" value={money(metrics.revenue_paise)} />
        <Metric label="AOV" value={money(metrics.aov_paise)} />
        <Metric label="Conversion" value={`${metrics.conversion_pct}%`} />
      </div>
    </div>
  );
}

function Metric({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.05em] text-zinc-600">
        {label}
      </div>
      <div className="mt-0.5 text-sm font-semibold text-zinc-200">{value}</div>
    </div>
  );
}
