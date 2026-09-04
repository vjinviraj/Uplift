export interface PurchaseRequest {
  query: string;
  budget_paise: number | null;
  category_hint: string | null;
  platform_hint: string | null;
  franchise_hint: string | null;
}

export interface PurchaseOfferBreakdownItem {
  product_id: string;
  name: string;
  qty: number;
  unit_price_paise: number;
  line_total_paise: number;
}

export type PolicyDecision =
  | "ALLOWED"
  | "REQUIRES_CONFIRMATION"
  | "REJECTED"
  | string;

export interface PurchaseOffer {
  product_id: string;
  upsell_product_id: string | null;
  upsell_reason: string | null;
  amount_paise: number;
  currency: string;
  breakdown: PurchaseOfferBreakdownItem[];
  policy_decision: PolicyDecision;
  policy_reason: string;
  policy_version: string;
}

export interface PurchasePreparationResponse {
  session_id: string;
  status: string;
  request: PurchaseRequest;
  offer: PurchaseOffer;
}

export interface PurchaseApprovalResponse {
  session_id: string;
  status: string;
  approved: boolean;
  amount_paise: number;
  currency: string;
  order_id: string | null;
  key_id: string | null;
  local_order_id: number | null;
}

export interface PurchasePaymentVerificationResponse {
  session_id: string;
  status: string;
  razorpay_order_id: string;
  razorpay_payment_id: string | null;
  message: string | null;
}

export interface OverviewTransaction {
  session_id: string;
  local_order_id: number;
  razorpay_order_id: string | null;
  product_name: string;
  amount_paise: number;
  currency: string;
  status: string;
}

export interface OverviewResponse {
  sessions: number;
  revenue_paise: number;
  aov_paise: number;
  upsell_acceptance_pct: number;
  upsell_orders: number;
  paid_orders: number;
  recent_transactions: OverviewTransaction[];
}

export interface TransactionPayment {
  id: number;
  razorpay_payment_id: string;
  status: string;
  method: string;
  verified_at: string | null;
  failure_reason: string | null;
}

export interface TransactionAuditEvent {
  id: number;
  timestamp: string;
  actor_type: string;
  action_id: string;
  event_type: string;
  decision: string | null;
  reason: string | null;
  policy_version: string | null;
  buyer_budget_paise: number | null;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  payload: Record<string, unknown>;
}

export interface TransactionResponse {
  session_id: string;
  status: string;

  request: PurchaseRequest;
  offer: PurchaseOffer;

  order_id: number | null;
  amount_paise: number;
  currency: string;
  order_status: string | null;
  razorpay_order_id: string | null;

  buyer_approval_amount_paise: number | null;
  buyer_approval_recorded: boolean;

  authorization_status: string;

  payments: TransactionPayment[];
  audit_events: TransactionAuditEvent[];
}

export interface AuditLogEvent {
  id: number;
  timestamp: string;
  session_id: string;
  actor_type: string;
  action_id: string;
  event_type: string;
  decision: string | null;
  reason: string | null;
  policy_version: string | null;
  buyer_budget_paise: number | null;
  razorpay_order_id: string | null;
  razorpay_payment_id: string | null;
  payload: Record<string, unknown>;
}

export interface AuditLogResponse {
  events: AuditLogEvent[];
}

export interface PurchaseRetryResponse {
  session_id: string;
  status: string;
  retry_count: number;
  amount_paise: number;
  currency: string;
  order_id: string;
  local_order_id: number;
  key_id: string;
}


export interface ExperimentArmMetrics {
  sessions: number;
  successful_orders: number;
  revenue_paise: number;
  aov_paise: number;
  conversion_pct: number;
}

export interface ExperimentSummaryResponse {
  methodology: string;
  treatment: ExperimentArmMetrics;
  control: ExperimentArmMetrics;
  aov_lift_pct: number | null;
  revenue_delta_per_session_paise: number | null;
  upsell_acceptance_pct: number;
  blocked_unsafe_actions: number;
  payment_recovery_pct: number | null;
}

