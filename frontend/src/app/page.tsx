import {
  Bot,
  Check,
  CircleHelp,
  CreditCard,
  LockKeyhole,
  Package,
  ShieldCheck,
  ShoppingBag,
  TrendingUp,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/uplift/AppShell";

const workflowSteps = [
  { label: "Request received", state: "done" },
  { label: "Catalog searched", state: "done" },
  { label: "Product selected", state: "done" },
  { label: "Upsell proposed", state: "done" },
  { label: "Price calculated", state: "done" },
  { label: "Policy ALLOWED", state: "done" },
  { label: "Awaiting buyer approval", state: "active" },
  { label: "Authorization", state: "pending" },
  { label: "Razorpay", state: "pending" },
  { label: "Verification", state: "pending" },
] as const;

function Panel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={[
        "rounded-xl border border-zinc-800 bg-[#0F0F10] p-5",
        className,
      ].join(" ")}
    >
      {children}
    </section>
  );
}

function PanelHeader({
  icon,
  children,
}: {
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="mb-3.5 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.07em] text-zinc-500">
      {icon}
      {children}
    </div>
  );
}

function ProductImage({
  type,
}: {
  type: "game" | "controller";
}) {
  return (
    <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg border border-zinc-800 bg-gradient-to-br from-[#18181B] to-[#222226] text-zinc-600">
      {type === "game" ? (
        <ShoppingBag className="h-5 w-5" strokeWidth={1.6} />
      ) : (
        <CreditCard className="h-5 w-5" strokeWidth={1.6} />
      )}
    </div>
  );
}

function CheckItem({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-[13px] text-zinc-400">
      <Check
        className="h-3.5 w-3.5 shrink-0 text-[#3FB950]"
        strokeWidth={2.4}
      />
      {children}
    </div>
  );
}

export default function Home() {
  return (
    <AppShell title="AI Buyer Checkout">
      <div className="mx-auto max-w-[1240px] p-5 md:p-7">
        <div className="mb-6">
          <h1 className="text-[26px] font-bold tracking-[-0.02em]">
            Checkout
          </h1>

          <p className="mt-1 max-w-4xl text-[13.5px] text-zinc-400">
            AI Buyer requests a product · Merchant Agent proposes an upsell ·
            Backend owns price, policy, and authorization
          </p>
        </div>

        <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
          {/* LEFT COLUMN */}
          <div className="space-y-4">
            <Panel>
              <PanelHeader
                icon={
                  <Bot className="h-3.5 w-3.5" strokeWidth={1.9} />
                }
              >
                AI Buyer
              </PanelHeader>

              <div className="mb-4 border-l-2 border-zinc-800 pl-3.5 text-[17px] font-medium leading-[1.4]">
                &quot;I want EA Sports FC under ₹2,500.&quot;
              </div>

              <div className="flex gap-7">
                <div>
                  <div className="mb-0.5 text-[11px] text-zinc-600">
                    Budget
                  </div>
                  <div className="text-[15px] font-semibold tabular-nums">
                    ₹2,500
                  </div>
                </div>

                <div>
                  <div className="mb-0.5 text-[11px] text-zinc-600">
                    Remaining after offer
                  </div>
                  <div className="text-[15px] font-semibold tabular-nums text-[#3FB950]">
                    ₹2
                  </div>
                </div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                icon={
                  <Package className="h-3.5 w-3.5" strokeWidth={1.9} />
                }
              >
                Product
              </PanelHeader>

              <div className="flex items-center gap-3.5 rounded-[10px] border border-zinc-800 p-3.5">
                <ProductImage type="game" />

                <div className="min-w-0 flex-1">
                  <div className="mb-0.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
                    Base product
                  </div>

                  <div className="text-[14.5px] font-semibold">
                    EA Sports FC
                  </div>
                </div>

                <div className="text-[15px] font-bold tabular-nums">
                  ₹999
                </div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                icon={
                  <TrendingUp className="h-3.5 w-3.5" strokeWidth={1.9} />
                }
              >
                Upsell
              </PanelHeader>

              <div className="flex items-center gap-3.5 rounded-[10px] border border-zinc-800 p-3.5">
                <ProductImage type="controller" />

                <div className="min-w-0 flex-1">
                  <div className="mb-0.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-zinc-600">
                    Suggested upsell
                  </div>

                  <div className="text-[14.5px] font-semibold">
                    Gaming Controller
                  </div>

                  <div className="mt-0.5 text-xs text-zinc-600">
                    Compatible with the selected product
                  </div>
                </div>

                <div className="text-[15px] font-bold tabular-nums">
                  ₹1,499
                </div>
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                icon={
                  <LockKeyhole className="h-3.5 w-3.5" strokeWidth={1.9} />
                }
              >
                Price
              </PanelHeader>

              <div className="space-y-0.5">
                <div className="flex justify-between py-1.5 text-[13.5px] text-zinc-400">
                  <span>Base product</span>
                  <span className="tabular-nums text-zinc-100">₹999</span>
                </div>

                <div className="flex justify-between py-1.5 text-[13.5px] text-zinc-400">
                  <span>Upsell</span>
                  <span className="tabular-nums text-zinc-100">₹1,499</span>
                </div>

                <div className="mt-1.5 flex justify-between border-t border-zinc-800 pt-3 text-[16px] font-bold">
                  <span>Server-computed total</span>
                  <span className="tabular-nums">₹2,498</span>
                </div>

                <div className="flex items-center gap-1.5 pt-1 text-[10.5px] text-zinc-600">
                  <ShieldCheck className="h-3 w-3" strokeWidth={1.9} />
                  Computed by backend — not derived from the LLM
                </div>
              </div>

              <div className="mt-[18px] flex gap-2.5">
                <Button
                  variant="outline"
                  className="h-11 w-[120px] border-zinc-800 bg-[#18181B] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                >
                  <X className="h-4 w-4" />
                  Reject
                </Button>

                <Button className="h-11 flex-1 bg-zinc-100 text-zinc-950 hover:bg-white">
                  <Check className="h-4 w-4" />
                  Approve ₹2,498
                </Button>
              </div>
            </Panel>
          </div>

          {/* RIGHT COLUMN */}
          <div className="space-y-4">
            <Panel>
              <PanelHeader
                icon={
                  <Bot className="h-3.5 w-3.5" strokeWidth={1.9} />
                }
              >
                Live Agent Workflow
              </PanelHeader>

              <div>
                {workflowSteps.map((step, index) => {
                  const isLast = index === workflowSteps.length - 1;

                  return (
                    <div key={step.label}>
                      <div className="flex items-start gap-3 py-[9px]">
                        <div
                          className={[
                            "mt-px flex h-5 w-5 shrink-0 items-center justify-center rounded-full",
                            step.state === "done"
                              ? "bg-[rgba(63,185,80,0.1)] text-[#3FB950]"
                              : step.state === "active"
                                ? "bg-[rgba(88,166,255,0.1)] text-[#58A6FF]"
                                : "border border-zinc-800 bg-[#18181B] text-zinc-600",
                          ].join(" ")}
                        >
                          {step.state === "done" ? (
                            <Check className="h-2.5 w-2.5" strokeWidth={3} />
                          ) : step.state === "active" ? (
                            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-current" />
                          ) : null}
                        </div>

                        <div
                          className={[
                            "text-[13.5px]",
                            step.state === "done"
                              ? "font-medium text-zinc-300"
                              : step.state === "active"
                                ? "font-semibold text-[#58A6FF]"
                                : "font-medium text-zinc-600",
                          ].join(" ")}
                        >
                          {step.label}
                        </div>
                      </div>

                      {!isLast && (
                        <div className="ml-[9px] h-3.5 w-px bg-zinc-800" />
                      )}
                    </div>
                  );
                })}
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                icon={
                  <CircleHelp className="h-3.5 w-3.5" strokeWidth={1.9} />
                }
              >
                Why This Upsell?
              </PanelHeader>

              <div className="space-y-2.5">
                <CheckItem>Compatible with selected product</CheckItem>
                <CheckItem>Deterministic merchant relationship</CheckItem>
                <CheckItem>Within autonomous upsell ceiling</CheckItem>
                <CheckItem>Final price validated by backend</CheckItem>
              </div>
            </Panel>

            <Panel>
              <PanelHeader
                icon={
                  <ShieldCheck className="h-3.5 w-3.5" strokeWidth={1.9} />
                }
              >
                Money Safety
              </PanelHeader>

              <div className="space-y-2.5">
                <CheckItem>Server-authoritative pricing</CheckItem>
                <CheckItem>Merchant policy enforced</CheckItem>
                <CheckItem>Buyer approval required</CheckItem>
                <CheckItem>Exact amount matched</CheckItem>
              </div>
            </Panel>
          </div>
        </div>
      </div>
    </AppShell>
  );
}