import type { PurchaseRequest } from "./types";

export type ScenarioId =
  | "successful_upsell"
  | "no_upsell"
  | "over_budget"
  | "policy_rejection"
  | "payment_failure";

export interface DemoScenario {
  id: ScenarioId;
  name: string;
  description: string;
  request: PurchaseRequest;
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "successful_upsell",
    name: "Successful upsell",
    description:
      "Treatment-style request for measuring agent-assisted basket value in Test Mode.",
    request: {
      query:
        "I'm looking for a small Genshin Impact accessory as a gift, and I'd like to keep the total under ₹5,000.",
      budget_paise: 500_000,
      category_hint: "Games",
      platform_hint: null,
      franchise_hint: "Genshin Impact",
    },
  },
  {
    id: "no_upsell",
    name: "No upsell",
    description:
      "Control-style request intended to constrain the merchant proposal and avoid upsell.",
    request: {
      query: "Genshin Impact",
      budget_paise: 50_000,
      category_hint: "Games",
      platform_hint: null,
      franchise_hint: "Genshin Impact",
    },
  },
  {
    id: "over_budget",
    name: "Over-budget proposal",
    description:
      "Known negative-path request where the deterministic total exceeds the buyer budget.",
    request: {
      query: "Genshin Impact",
      budget_paise: 100_000,
      category_hint: "Games",
      platform_hint: null,
      franchise_hint: "Genshin Impact",
    },
  },
  {
    id: "policy_rejection",
    name: "Policy rejection",
    description:
      "Uses the known policy-rejection safety case; authorization must stop before Razorpay.",
    request: {
      query: "Genshin Impact",
      budget_paise: 100_000,
      category_hint: "Games",
      platform_hint: null,
      franchise_hint: "Genshin Impact",
    },
  },
  {
    id: "payment_failure",
    name: "Payment failure → retry",
    description:
      "Runs the successful purchase request so the Test Mode payment failure path can be demonstrated.",
    request: {
      query:
        "I'm looking for a small Genshin Impact accessory as a gift, and I'd like to keep the total under ₹5,000.",
      budget_paise: 500_000,
      category_hint: "Games",
      platform_hint: null,
      franchise_hint: "Genshin Impact",
    },
  },
];

export function getScenario(id: string | null) {
  return (
    DEMO_SCENARIOS.find((scenario) => scenario.id === id) ??
    DEMO_SCENARIOS[0]
  );
}