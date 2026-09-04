import type {
  AuditLogResponse,
  OverviewResponse,
  PurchaseApprovalResponse,
  PurchasePaymentVerificationResponse,
  PurchasePreparationResponse,
  PurchaseRequest,
  PurchaseRetryResponse,
  TransactionResponse,
  ExperimentSummaryResponse,
} from "./types";

  const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ?? "http://127.0.0.1:8000";

  async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;

    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        ...init,
        headers: {
          "Content-Type": "application/json",
          ...(init?.headers ?? {}),
        },
      });
    } catch {
      throw new Error(
        "Unable to reach the Uplift API. Make sure the FastAPI server is running.",
      );
    }

    const body = (await response.json().catch(() => null)) as
      | { detail?: string }
      | T
      | null;

    if (!response.ok) {
      const detail =
        body && typeof body === "object" && "detail" in body
          ? body.detail
          : undefined;
      throw new Error(
        typeof detail === "string"
          ? detail
          : `Uplift API request failed (${response.status})`,
      );
    }

    return body as T;
  }

  export function createPurchase(
    request: PurchaseRequest,
  ): Promise<PurchasePreparationResponse> {
    return apiFetch<PurchasePreparationResponse>("/api/purchases/prepare", {
      method: "POST",
      body: JSON.stringify(request),
    });
  }

  export function getOffer(
    sessionId: string,
  ): Promise<PurchasePreparationResponse> {
    return apiFetch<PurchasePreparationResponse>(
      `/api/purchases/${encodeURIComponent(sessionId)}`,
    );
  }

  export function approvePurchase(
    sessionId: string,
    approved: boolean,
    amountPaise: number,
  ): Promise<PurchaseApprovalResponse> {
    return apiFetch<PurchaseApprovalResponse>(
      `/api/purchases/${encodeURIComponent(sessionId)}/approve`,
      {
        method: "POST",
        body: JSON.stringify({
          approved,
          amount_paise: amountPaise,
        }),
      },
    );
  }

  export function verifyPurchasePayment(
    sessionId: string,
    razorpayPaymentId: string,
    razorpayOrderId: string,
    razorpaySignature: string,
  ): Promise<PurchasePaymentVerificationResponse> {
    return apiFetch<PurchasePaymentVerificationResponse>(
      `/api/purchases/${encodeURIComponent(sessionId)}/verify`,
      {
        method: "POST",
        body: JSON.stringify({
          razorpay_payment_id: razorpayPaymentId,
          razorpay_order_id: razorpayOrderId,
          razorpay_signature: razorpaySignature,
        }),
      },
    );
  }

  export function getOverview(): Promise<OverviewResponse> {
  return apiFetch<OverviewResponse>("/api/overview");
}

export function getTransaction(
  sessionId: string,
): Promise<TransactionResponse> {
  return apiFetch<TransactionResponse>(
    `/api/transactions/${encodeURIComponent(sessionId)}`,
  );
}

export function getAuditLog(): Promise<AuditLogResponse> {
  return apiFetch<AuditLogResponse>("/api/audit");
}

export function recordPaymentFailure(
  razorpayPaymentId: string,
  razorpayOrderId: string,
): Promise<{
  status: string;
  order_id: string;
  payment_id: string;
  failure_reason: string | null;
}> {
  return apiFetch("/test/razorpay/failure", {
    method: "POST",
    body: JSON.stringify({
      razorpay_payment_id: razorpayPaymentId,
      razorpay_order_id: razorpayOrderId,
    }),
  });
}

export function retryPurchase(
  sessionId: string,
): Promise<PurchaseRetryResponse> {
  return apiFetch(
    `/api/purchases/${encodeURIComponent(sessionId)}/retry`,
    {
      method: "POST",
    },
  );
}
export function getExperimentSummary(): Promise<ExperimentSummaryResponse> {
  return apiFetch<ExperimentSummaryResponse>("/api/experiment/summary");
}
