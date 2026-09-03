from sqlmodel import Session

from apps.api.agents.llm_client import LLMClient
from apps.api.agents.schemas import (
    MerchantAgentProposal,
    PurchaseOffer,
    PurchaseRequest,
)
from apps.api.agents.tool_schemas import (
    GetUpsellCandidatesOutput,
    PriceOrderOutput,
    SearchCatalogOutput,
)
from apps.api.commerce.catalog import (
    get_upsell_candidates,
    price_order,
    search_catalog,
)
from apps.api.models import PolicyConfig
from apps.api.policy.engine import check_policy


class MerchantAgent:
    """Orchestrate LLM proposals through deterministic commerce controls."""

    MAX_REPROMPTS = 1

    def __init__(self, llm_client: LLMClient) -> None:
        self.llm_client = llm_client

    def propose(
        self,
        *,
        session: Session,
        request: PurchaseRequest,
        policy: PolicyConfig,
    ) -> PurchaseOffer:
        """Create a policy-evaluated purchase offer from a buyer request."""

        if request.budget_paise is None:
            raise ValueError(
                "buyer_budget_paise is required for Merchant Agent policy evaluation"
            )

        search_output = SearchCatalogOutput.model_validate(
            search_catalog(
                session,
                request.query,
                category_hint=request.category_hint,
            )
        )

        if not search_output.matches:
            raise ValueError("No catalog products matched the purchase request")

        proposal = self._get_valid_proposal(
            request=request,
            search_output=search_output,
            session=session,
        )

        candidate_output = GetUpsellCandidatesOutput.model_validate(
            get_upsell_candidates(session, proposal.product_id)
        )

        upsell = None
        if proposal.upsell is not None:
            upsell = next(
                (
                    candidate
                    for candidate in candidate_output.candidates
                    if candidate.product_id == proposal.upsell.product_id
                ),
                None,
            )

            if upsell is None:
                raise ValueError(
                    "Merchant Agent selected an upsell that is not a valid mapped candidate"
                )

        line_items = [{"product_id": proposal.product_id, "qty": 1}]
        if upsell is not None:
            line_items.append({"product_id": upsell.product_id, "qty": 1})

        price_output = PriceOrderOutput.model_validate(
            price_order(session, line_items)
        )

        policy_result = check_policy(
            policy=policy,
            total_paise=price_output.amount_paise,
            buyer_budget_paise=request.budget_paise,
            upsell_count=1 if upsell is not None else 0,
            upsell_price_paise=upsell.price_paise if upsell is not None else 0,
            product_ids=[item.product_id for item in price_output.breakdown],
        )

        return PurchaseOffer(
            product_id=proposal.product_id,
            upsell_product_id=upsell.product_id if upsell is not None else None,
            upsell_reason=proposal.upsell.reason if upsell is not None else None,
            amount_paise=price_output.amount_paise,
            currency=price_output.currency,
            breakdown=[
                item.model_dump()
                for item in price_output.breakdown
            ],
            policy_decision=policy_result.decision,
            policy_reason=policy_result.reason,
            policy_version=policy_result.policy_version,
        )

    def _get_valid_proposal(
        self,
        *,
        request: PurchaseRequest,
        search_output: SearchCatalogOutput,
        session: Session,
    ) -> MerchantAgentProposal:
        """Ask the LLM for a proposal and allow exactly one corrective retry."""

        context = self._build_context(
            request=request,
            search_output=search_output,
            session=session,
        )

        last_error: Exception | None = None

        for attempt in range(self.MAX_REPROMPTS + 1):
            try:
                proposal = self.llm_client.generate_structured(
                    system_prompt=self._system_prompt(),
                    user_prompt=self._user_prompt(context, error=last_error),
                    response_model=MerchantAgentProposal,
                )
                return self._validate_proposal_against_context(
                    proposal,
                    search_output=search_output,
                    session=session,
                )
            except ValueError as exc:
                last_error = exc
                if attempt >= self.MAX_REPROMPTS:
                    raise ValueError(
                        "Merchant Agent proposal remained invalid after one re-prompt"
                    ) from exc

        raise RuntimeError("Unreachable Merchant Agent retry state")

    @staticmethod
    def _validate_proposal_against_context(
        proposal: MerchantAgentProposal,
        *,
        search_output: SearchCatalogOutput,
        session: Session,
    ) -> MerchantAgentProposal:
        allowed_base_ids = {
            match.product_id for match in search_output.matches
        }
        if proposal.product_id not in allowed_base_ids:
            raise ValueError(
                "Selected base product must be one of the returned catalog matches"
            )

        candidate_output = GetUpsellCandidatesOutput.model_validate(
            get_upsell_candidates(session, proposal.product_id)
        )
        allowed_upsell_ids = {
            candidate.product_id for candidate in candidate_output.candidates
        }

        if (
            proposal.upsell is not None
            and proposal.upsell.product_id not in allowed_upsell_ids
        ):
            raise ValueError(
                "Selected upsell must be one of the deterministic mapped candidates"
            )

        return proposal

    @staticmethod
    def _system_prompt() -> str:
        return (
            "You are the merchant-side gaming commerce agent. "
            "Return only the requested structured proposal. "
            "Select the best base product from the supplied catalog options. "
            "If an upsell is appropriate, select at most one from the supplied "
            "deterministic compatibility candidates. "
            "Do not invent products, compatibility, prices, discounts, policy "
            "decisions, authorization, or Razorpay actions. "
            "Prices are computed later by the backend."
        )

    @staticmethod
    def _build_context(
        *,
        request: PurchaseRequest,
        search_output: SearchCatalogOutput,
        session: Session,
    ) -> str:
        options = []

        for match in search_output.matches:
            candidate_output = GetUpsellCandidatesOutput.model_validate(
                get_upsell_candidates(session, match.product_id)
            )
            options.append(
                {
                    "product_id": match.product_id,
                    "name": match.name,
                    "upsell_candidates": [
                        {
                            "product_id": candidate.product_id,
                            "name": candidate.name,
                            "reason_code": candidate.reason_code,
                        }
                        for candidate in candidate_output.candidates
                    ],
                }
            )

        return (
            f"Buyer request: {request.model_dump_json()}\n"
            f"Catalog options: {options}"
        )

    @staticmethod
    def _user_prompt(
        context: str,
        *,
        error: Exception | None = None,
    ) -> str:
        correction = ""
        if error is not None:
            correction = (
                "\nYour previous proposal was invalid. Correct this exact problem: "
                f"{error}. Return a corrected proposal using only the supplied IDs."
            )

        return (
            "Choose the best base product for the buyer request and, when relevant, "
            "choose at most one compatible upsell. The upsell must be one of the "
            "supplied deterministic candidates. Do not provide price information.\n\n"
            f"{context}{correction}"
        )
