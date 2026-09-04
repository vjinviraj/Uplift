"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { getScenario } from "@/lib/scenarios";
import Script from "next/script";
import Image from "next/image";
import {
  Bot,
  Check,
  CircleHelp,
  CreditCard,
  LockKeyhole,
  Package,
  ShieldCheck,
  TrendingUp,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { AppShell } from "@/components/uplift/AppShell";
import {
  approvePurchase,
  createPurchase,
  recordPaymentFailure,
  retryPurchase,
  verifyPurchasePayment,
} from "@/lib/api";
import type { PurchaseOffer } from "@/lib/types";

function formatMoney(paise: number, currency = "INR") {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(paise / 100);
}

function productImagePath(productId: string) {
  return `/products/${productId}-clean.png`;
}

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
  productId,
  className = "",
}: {
  productId: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  return (
    <div
      className={[
        "relative flex items-center justify-center overflow-hidden",
        className,
      ].join(" ")}
    >
      {failed ? (
        <Package className="h-8 w-8 text-zinc-600" strokeWidth={1.5} />
      ) : (
        <Image
          src={productImagePath(productId)}
          alt=""
          fill
          className="object-contain p-4"
          sizes="(min-width: 768px) 50vw, 100vw"
          onError={() => setFailed(true)}
        />
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

function CheckoutContent() {
  const searchParams = useSearchParams();
  const scenario = getScenario(searchParams.get("scenario"));
  const request = scenario.request;
  const [offer, setOffer] = useState<PurchaseOffer | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState("LOADING");
  const [error, setError] = useState<string | null>(null);
  const [approvalState, setApprovalState] = useState<
    "idle" | "working" | "approved" | "rejected"
  >("idle");
  const [orderId, setOrderId] = useState<string | null>(null);
  const [failedOrderId, setFailedOrderId] = useState<string | null>(null);
  const [retryOrderId, setRetryOrderId] = useState<string | null>(null);
  const [paymentStatus, setPaymentStatus] = useState<
    "idle" | "opening" | "verifying" | "paid" | "failed"
  >("idle");
  const [paymentMessage, setPaymentMessage] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [retryState, setRetryState] = useState<
    "idle" | "working" | "exhausted"
  >("idle");

  useEffect(() => {
    let cancelled = false;

    async function loadOffer() {
      try {
        const response = await createPurchase(request);
        if (cancelled) return;

        setSessionId(response.session_id);
        setOffer(response.offer);
        setStatus(response.status);
      } catch (err) {
        if (cancelled) return;

        setError(
          err instanceof Error ? err.message : "Unable to load purchase offer.",
        );
        setStatus("FAILED");
      }
    }

    void loadOffer();

    return () => {
      cancelled = true;
    };
  }, [request]);

  const baseItem = offer?.breakdown[0] ?? null;
  const upsellItem = offer?.breakdown[1] ?? null;

  const remaining =
    request.budget_paise !== null && offer
      ? request.budget_paise - offer.amount_paise
      : null;

  const workflowSteps = useMemo(() => {
    if (status === "LOADING") {
      return [
        { label: "Request processing", state: "active" },
        { label: "Offer awaiting response", state: "pending" },
        { label: "Authorization", state: "pending" },
        { label: "Razorpay", state: "pending" },
        { label: "Verification", state: "pending" },
      ] as const;
    }

    if (status === "FAILED") {
      return [
        { label: "Request failed", state: "active" },
        { label: "Offer", state: "pending" },
        { label: "Authorization", state: "pending" },
        { label: "Razorpay", state: "pending" },
        { label: "Verification", state: "pending" },
      ] as const;
    }

    if (approvalState === "approved") {
      return [
        { label: "Request received", state: "done" },
        { label: "Catalog + pricing", state: "done" },
        { label: "Policy", state: "done" },
        { label: "Buyer approved exact amount", state: "done" },
        { label: "Razorpay order created", state: "done" },
        {
          label: "Checkout",
          state:
            paymentStatus === "paid"
              ? "done"
              : paymentStatus === "failed"
                ? "active"
                : "active",
        },
        {
          label: "Verification",
          state:
            paymentStatus === "paid"
              ? "done"
              : paymentStatus === "verifying"
                ? "active"
                : "pending",
        },
      ] as const;
    }

    if (approvalState === "rejected") {
      return [
        { label: "Request received", state: "done" },
        { label: "Catalog + pricing", state: "done" },
        { label: "Policy", state: "done" },
        { label: "Buyer rejected offer", state: "done" },
        { label: "Payment", state: "skipped" },
      ] as const;
    }

    return [
      { label: "Request received", state: "done" },
      { label: "Catalog + pricing", state: "done" },
      {
        label: "Policy",
        state: offer?.policy_decision === "ALLOWED" ? "done" : "active",
      },
      { label: "Awaiting buyer approval", state: "active" },
      { label: "Authorization", state: "pending" },
      { label: "Razorpay", state: "pending" },
      { label: "Verification", state: "pending" },
    ] as const;
  }, [approvalState, offer?.policy_decision, paymentStatus, status]);

  async function handleApproval(approved: boolean) {
    if (
      !sessionId ||
      !offer ||
      approvalState === "working" ||
      approvalState === "approved"
    ) {
      return;
    }

    setApprovalState("working");
    setError(null);

    try {
      const response = await approvePurchase(
        sessionId,
        approved,
        offer.amount_paise,
      );

      if (!approved) {
        setApprovalState("rejected");
        setStatus(response.status);
        return;
      }

      setApprovalState(response.approved ? "approved" : "rejected");
      setStatus(response.status);
      setOrderId(response.order_id);

      if (response.approved && response.order_id && response.key_id) {
        openRazorpayCheckout({
          order_id: response.order_id,
          key_id: response.key_id,
          amount_paise: response.amount_paise,
          currency: response.currency,
        });
      }
    } catch (err) {
      setApprovalState("idle");
      setError(err instanceof Error ? err.message : "Approval failed.");
    }
  }

  function openRazorpayCheckout(order: {
    order_id: string;
    key_id: string;
    amount_paise: number;
    currency: string;
  }) {
    if (!window.Razorpay) {
      setError("Razorpay Checkout is still loading. Please try again.");
      setPaymentStatus("failed");
      return;
    }

    setPaymentStatus("opening");
    setPaymentMessage(null);

    const razorpay = new window.Razorpay({
      key: order.key_id,
      amount: order.amount_paise,
      currency: order.currency,
      name: "Uplift",
      description: "AI-powered gaming commerce purchase",
      image: `${window.location.origin}/brand/uplift-logo.png`,
      order_id: order.order_id,

      handler: async (response) => {
        setPaymentStatus("verifying");
        setPaymentMessage("Signature received. Verifying payment server-side…");

        try {
          if (!sessionId) {
            throw new Error("Purchase session is missing.");
          }

          const verification = await verifyPurchasePayment(
            sessionId,
            response.razorpay_payment_id,
            response.razorpay_order_id,
            response.razorpay_signature,
          );

          if (verification.status !== "PAID") {
            setPaymentStatus("failed");
            setPaymentMessage(
              verification.message ?? "Payment is not yet captured.",
            );
            setStatus(verification.status);
            return;
          }

          setPaymentStatus("paid");
          setPaymentMessage(
            verification.message ?? "Payment verified and reconciled.",
          );
          setStatus("PAID");
        } catch (err) {
          setPaymentStatus("failed");
          setPaymentMessage(
            err instanceof Error ? err.message : "Payment verification failed.",
          );
        }
      },
    });

    razorpay.on("payment.failed", (response) => {
      console.log("Razorpay payment.failed response", response);

      const reason =
        response.error?.description ??
        response.error?.reason ??
        "Payment failed.";

      setPaymentStatus("failed");
      setPaymentMessage(reason);
      setStatus("PAYMENT_FAILED");

      // Track the failed Order separately
      setFailedOrderId(order.order_id);

      void (async () => {
        try {
          const paymentId = response.error?.metadata?.payment_id ?? "";

          const orderIdFromResponse =
            response.error?.metadata?.order_id ?? order.order_id;

          await recordPaymentFailure(paymentId, orderIdFromResponse);

          setRetryState("idle");
          setPaymentMessage(
            `${reason} You can retry this payment once with a new Razorpay order.`,
          );
        } catch (err) {
          setRetryState("exhausted");
          setPaymentMessage(
            err instanceof Error
              ? err.message
              : "Payment failed and could not be recorded by the server.",
          );
        }
      })();
    });

    razorpay.open();
  }

  async function handleRetry() {
    if (!sessionId || retryCount >= 1 || retryState === "working") {
      return;
    }

    setRetryState("working");
    setError(null);
    setPaymentMessage("Creating a fresh Razorpay order…");

    try {
      const response = await retryPurchase(sessionId);

      setRetryCount(response.retry_count);
      setRetryState("idle");

      // Save the retry Order separately
      setRetryOrderId(response.order_id);
      setOrderId(response.order_id);
      setStatus(response.status);
      setPaymentStatus("idle");
      setPaymentMessage(
        `Retry order created. New Razorpay Order: ${response.order_id}`,
      );

      openRazorpayCheckout({
        order_id: response.order_id,
        key_id: response.key_id,
        amount_paise: response.amount_paise,
        currency: response.currency,
      });
    } catch (err) {
      setRetryState("exhausted");
      setPaymentStatus("failed");
      setPaymentMessage(
        err instanceof Error
          ? err.message
          : "Unable to create the retry order.",
      );
    }
  }

  return (
    <>
      <Script
        src="https://checkout.razorpay.com/v1/checkout.js"
        strategy="afterInteractive"
      />

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

          {error && (
            <div className="mb-4 rounded-xl border border-red-950 bg-red-950/20 px-4 py-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <div className="grid items-start gap-5 lg:grid-cols-[minmax(0,1fr)_380px]">
            <div className="space-y-4">
              <Panel>
                <PanelHeader
                  icon={<Bot className="h-3.5 w-3.5" strokeWidth={1.9} />}
                >
                  AI Buyer
                </PanelHeader>

                <div className="mb-3 inline-flex items-center rounded-md border border-zinc-800 bg-[#18181B] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.06em] text-zinc-500">
                  Scenario · {scenario.name}
                </div>

                <div className="mb-4 border-l-2 border-zinc-800 pl-3.5 text-[17px] font-medium leading-[1.4]">
                  &quot;{request.query}&quot;
                </div>

                <div className="flex gap-7">
                  <div>
                    <div className="mb-0.5 text-[11px] text-zinc-600">
                      Budget
                    </div>

                    <div className="text-[15px] font-semibold tabular-nums">
                      {formatMoney(request.budget_paise ?? 0)}
                    </div>
                  </div>

                  <div>
                    <div className="mb-0.5 text-[11px] text-zinc-600">
                      Remaining after offer
                    </div>

                    <div
                      className={`text-[15px] font-semibold tabular-nums ${
                        remaining !== null && remaining >= 0
                          ? "text-[#3FB950]"
                          : "text-red-400"
                      }`}
                    >
                      {remaining === null ? "—" : formatMoney(remaining)}
                    </div>
                  </div>
                </div>
              </Panel>

              <Panel>
                <PanelHeader
                  icon={<Package className="h-3.5 w-3.5" strokeWidth={1.9} />}
                >
                  Product &amp; Upsell
                </PanelHeader>

                <div className="relative">
                  <div className="grid gap-4 md:grid-cols-2">
                    {baseItem ? (
                      <div className="overflow-hidden rounded-xl border border-zinc-800 bg-[#111112]">
                        <div className="relative flex h-[230px] items-center justify-center border-b border-zinc-800 bg-[#171719]">
                          <ProductImage
                            productId={baseItem.product_id}
                            className="h-full w-full"
                          />
                          <div className="absolute left-4 top-4 rounded-md border border-zinc-700 bg-[#0F0F10]/90 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-zinc-300">
                            Base product
                          </div>
                        </div>

                        <div className="p-4">
                          <div className="min-h-[44px] text-[15px] font-semibold leading-5 text-zinc-100">
                            {baseItem.name}
                          </div>
                          <div className="mt-3 text-[20px] font-bold tabular-nums text-zinc-50">
                            {formatMoney(
                              baseItem.line_total_paise,
                              offer?.currency,
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex min-h-[300px] items-center justify-center rounded-xl border border-zinc-800 text-sm text-zinc-600">
                        Waiting for backend offer…
                      </div>
                    )}

                    {upsellItem ? (
                      <div className="overflow-hidden rounded-xl border border-[#3FB950]/25 bg-[#111112]">
                        <div className="relative flex h-[230px] items-center justify-center border-b border-zinc-800 bg-[#171719]">
                          <ProductImage
                            productId={upsellItem.product_id}
                            className="h-full w-full"
                          />
                          <div className="absolute left-4 top-4 rounded-md border border-[#3FB950]/30 bg-[#0F0F10]/90 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[0.06em] text-zinc-300">
                            Suggested upsell
                          </div>
                        </div>

                        <div className="p-4">
                          <div className="min-h-[44px] text-[15px] font-semibold leading-5 text-zinc-100">
                            {upsellItem.name}
                          </div>
                          <div className="mt-1 line-clamp-2 min-h-[32px] text-xs leading-4 text-zinc-500">
                            {offer?.upsell_reason ??
                              "Deterministic merchant relationship"}
                          </div>
                          <div className="mt-3 text-[20px] font-bold tabular-nums text-zinc-50">
                            {formatMoney(
                              upsellItem.line_total_paise,
                              offer?.currency,
                            )}
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex min-h-[300px] items-center justify-center rounded-xl border border-zinc-800 text-sm text-zinc-600">
                        No upsell in this offer.
                      </div>
                    )}
                  </div>

                  {baseItem && upsellItem && (
                    <div className="pointer-events-none absolute left-1/2 top-1/2 z-20 hidden -translate-x-1/2 -translate-y-1/2 md:flex">
                      <div className="flex h-9 w-9 items-center justify-center rounded-full border border-zinc-700 bg-[#0F0F10] text-sm font-bold text-zinc-300 shadow-lg">
                        +
                      </div>
                    </div>
                  )}
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
                  {offer?.breakdown.map((item) => (
                    <div
                      key={item.product_id}
                      className="flex justify-between py-1.5 text-[13.5px] text-zinc-400"
                    >
                      <span>{item.name}</span>

                      <span className="tabular-nums text-zinc-100">
                        {formatMoney(item.line_total_paise, offer.currency)}
                      </span>
                    </div>
                  ))}

                  <div className="mt-1.5 flex justify-between border-t border-zinc-800 pt-3 text-[16px] font-bold">
                    <span>Server-computed total</span>

                    <span className="tabular-nums">
                      {offer
                        ? formatMoney(offer.amount_paise, offer.currency)
                        : "—"}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 pt-1 text-[10.5px] text-zinc-600">
                    <ShieldCheck className="h-3 w-3" strokeWidth={1.9} />
                    Computed by backend — not derived from the UI
                  </div>
                </div>

                <div className="mt-[18px] flex gap-2.5">
                  <Button
                    variant="outline"
                    onClick={() => void handleApproval(false)}
                    disabled={
                      !offer ||
                      approvalState === "working" ||
                      approvalState === "approved" ||
                      approvalState === "rejected"
                    }
                    className="h-11 w-[120px] border-zinc-800 bg-[#18181B] text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100"
                  >
                    <X className="h-4 w-4" />
                    Reject
                  </Button>

                  <Button
                    onClick={() => void handleApproval(true)}
                    disabled={
                      !offer ||
                      approvalState === "working" ||
                      approvalState === "approved" ||
                      approvalState === "rejected" ||
                      offer.policy_decision === "REJECTED"
                    }
                    className="h-11 flex-1 bg-zinc-100 text-zinc-950 hover:bg-white"
                  >
                    <Check className="h-4 w-4" />

                    {approvalState === "working"
                      ? "Authorizing…"
                      : approvalState === "approved"
                        ? "Approved"
                        : `Approve ${
                            offer
                              ? formatMoney(offer.amount_paise, offer.currency)
                              : "offer"
                          }`}
                  </Button>
                </div>
              </Panel>

              {orderId && (
                <Panel>
                  <PanelHeader
                    icon={
                      <CreditCard className="h-3.5 w-3.5" strokeWidth={1.9} />
                    }
                  >
                    Razorpay
                  </PanelHeader>

                  <div className="text-sm text-zinc-400">
                    {paymentStatus === "paid"
                      ? "Payment verified and reconciled."
                      : paymentStatus === "verifying"
                        ? "Payment completed. Verifying server-side…"
                        : paymentStatus === "failed"
                          ? "Payment failed or could not be verified."
                          : paymentStatus === "opening"
                            ? "Opening Test Mode Checkout…"
                            : "Test Mode order created."}
                  </div>

                  {/* Show both Failed and Retry Orders when applicable */}
                  {failedOrderId && retryOrderId ? (
                    <div className="mt-2 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-zinc-500">
                          Failed Order
                        </span>
                        <span className="font-mono text-xs text-red-400">
                          {failedOrderId}
                        </span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-zinc-500">
                          Retry Order
                        </span>
                        <span className="font-mono text-xs text-[#3FB950]">
                          {retryOrderId}
                        </span>
                      </div>
                    </div>
                  ) : (
                    <div className="mt-2 break-all font-mono text-xs text-zinc-600">
                      {orderId}
                    </div>
                  )}

                  {paymentMessage && (
                    <div className="mt-3 rounded-lg border border-zinc-800 bg-[#18181B] px-3 py-2 text-xs text-zinc-400">
                      {paymentMessage}
                    </div>
                  )}

                  {paymentStatus === "failed" &&
                    retryCount === 0 &&
                    retryState !== "exhausted" && (
                      <Button
                        onClick={() => void handleRetry()}
                        disabled={retryState === "working"}
                        className="mt-3 h-9 bg-zinc-100 text-zinc-950 hover:bg-white"
                      >
                        {retryState === "working"
                          ? "Creating Retry Order…"
                          : "Try Checkout Again"}
                      </Button>
                    )}

                  {retryCount >= 1 && paymentStatus === "failed" && (
                    <div className="mt-3 rounded-lg border border-zinc-800 bg-[#18181B] px-3 py-2 text-xs text-zinc-500">
                      Retry limit reached. No additional payment attempt will be
                      created.
                    </div>
                  )}
                </Panel>
              )}
            </div>

            <div className="space-y-4">
              <Panel>
                <PanelHeader
                  icon={<Bot className="h-3.5 w-3.5" strokeWidth={1.9} />}
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
                                  : step.state === "skipped"
                                    ? "border border-zinc-800 bg-[#18181B] text-zinc-700"
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
                                  : step.state === "skipped"
                                    ? "font-medium text-zinc-700 line-through"
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

                {offer?.upsell_product_id ? (
                  <div className="space-y-2.5">
                    <CheckItem>
                      Selected from deterministic catalog relationships
                    </CheckItem>

                    <CheckItem>
                      {offer.upsell_reason ?? "Relevant to the buyer request"}
                    </CheckItem>

                    <CheckItem>Final price validated by backend</CheckItem>
                  </div>
                ) : (
                  <div className="text-[13px] text-zinc-600">
                    The backend returned no upsell for this request.
                  </div>
                )}
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

                  <CheckItem>
                    Buyer approval requires the exact amount
                  </CheckItem>

                  <CheckItem>
                    Payment order created only after authorization
                  </CheckItem>
                </div>
              </Panel>
            </div>
          </div>
        </div>
      </AppShell>
    </>
  );
}

export default function Home() {
  return (
    <Suspense fallback={null}>
      <CheckoutContent />
    </Suspense>
  );
}