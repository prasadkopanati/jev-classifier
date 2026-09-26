"""The fixed classification metrics. This is the only place they are defined."""

import copy
from typing import Any

from app.config import JEV_MODEL

QUESTIONS: dict[str, dict[str, Any]] = {
    "intent": {
        "type": "choice",
        "instructions": "What is the main intent of the customer's message?",
        "criteria": {
            "billing": "Charges, invoices, payments, refunds or subscription billing",
            "technical": "Bugs, errors, outages or integration problems",
            "sales": "Pricing, plans, upgrades or buying questions",
            "general_inquiry": "A general question or information request that fits none of the others",
            "complaint": "Dissatisfaction with the service, staff or product that is not mainly about billing or a technical fault",
        },
    },
    "department": {
        "type": "choice",
        "instructions": "Which department should handle this message?",
        "criteria": {
            "billing": "Handles payments, charges, invoices and refunds",
            "technical": "Handles bugs, errors and integration problems",
            "sales": "Handles pricing, plans and new purchases",
        },
    },
    "frustration": {
        "type": "score",
        "instructions": "How frustrated does the customer appear?",
        "criteria": [
            "Calm, just stating facts",
            "Frustrated but civil",
            "Very angry, strong language",
        ],
    },
    "is_urgent": {
        "type": "noul",
        "instructions": "The message conveys urgency or time-sensitivity",
    },
    "refund_requested": {
        "type": "noul",
        "instructions": "The customer asks for money back or a charge reversal",
    },
    "wants_human": {
        "type": "noul",
        "instructions": "The customer asks for a human agent or escalation",
    },
    "churn_risk": {
        "type": "noul",
        "instructions": "The customer threatens to cancel or leave",
    },
}


def build_request(text: str) -> dict[str, Any]:
    """Build the /systemone request body for the customer's text."""
    return {
        "model": JEV_MODEL,
        "state": text,
        "questions": copy.deepcopy(QUESTIONS),
    }
