"""GenerateSystemUnderstandingTask: synthesizes all analysis into a comprehensive document.

This is the core output of the Discovery Agent — a deep, detailed document
that the Design Agent will use as its primary input.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.task import BaseTask


class SystemUnderstandingInput(BaseModel):
    deep_analysis: dict[str, Any]  # DeepAnalysisResult as dict


class UserJourney(BaseModel):
    journey_name: str = ""
    actor: str = ""
    steps: list[str] = Field(default_factory=list)
    business_rules_applied: list[str] = Field(default_factory=list)


class IntegrationPoint(BaseModel):
    system_name: str = ""
    integration_type: str = ""  # API, file_transfer, database, message_queue
    description: str = ""
    data_exchanged: list[str] = Field(default_factory=list)


class ModernizationRecommendation(BaseModel):
    area: str = ""
    recommendation: str = ""
    rationale: str = ""
    trade_offs: str = ""
    priority: str = "medium"  # high, medium, low


class SystemUnderstanding(BaseModel):
    system_purpose: str = ""
    domain_model: str = ""
    business_rules_catalog: list[dict[str, Any]] = Field(default_factory=list)
    technology_assessment: str = ""
    user_workflows: list[UserJourney] = Field(default_factory=list)
    data_flow_description: str = ""
    integration_points: list[IntegrationPoint] = Field(default_factory=list)
    modernization_recommendations: list[ModernizationRecommendation] = Field(
        default_factory=list
    )


class GenerateSystemUnderstandingTask(
    BaseTask[SystemUnderstandingInput, SystemUnderstanding]
):
    """Synthesizes deep analysis results into a comprehensive system understanding."""

    name = "generate_system_understanding"
    description = (
        "Synthesize all extraction and analysis results into a comprehensive "
        "system understanding document suitable for the Design Agent"
    )
    input_schema = SystemUnderstandingInput
    output_schema = SystemUnderstanding
    max_retries = 1  # Expensive LLM call, limit retries

    prompt_template = """\
Synthesize the following analysis results into a comprehensive system understanding.

This is NOT a summary. Each section should be detailed and thorough:

1. **system_purpose**: 2-3 paragraphs explaining what the system does, who uses it, \
and why it exists. Include the business domain, key value propositions, and critical \
success factors.

2. **domain_model**: Narrative description of all domain entities and how they \
relate to each other. Describe the entity lifecycle, state transitions, and \
ownership hierarchies.

3. **business_rules_catalog**: Organized list of ALL business rules grouped by \
domain area. Each rule must include trigger_condition, action, exceptions, and \
validation_logic.

4. **technology_assessment**: Current tech stack analysis including strengths, \
weaknesses, technical debt, security concerns, and scalability limits.

5. **user_workflows**: Step-by-step user journeys for EVERY identified user role. \
Include happy path, error paths, and which business rules apply at each step.

6. **data_flow_description**: How data moves through the system from input to \
storage to output. Include data transformations, validation points, and \
persistence boundaries.

7. **integration_points**: All external systems the application communicates with, \
including integration type, protocol, data format, and error handling approach.

8. **modernization_recommendations**: Specific recommendations with rationale and \
trade-offs. Prioritize by business impact and implementation complexity.

{deep_analysis}"""

    few_shot_examples = [
        {
            "input": {"deep_analysis": {"business_rules": [{"rule_name": "login_lockout"}]}},
            "output": {
                "system_purpose": "The Acme Order Management System is a B2B platform that enables wholesale distributors to place, track, and manage purchase orders with their suppliers. The system serves three primary user roles: buyers who create and submit orders, account managers who approve orders exceeding credit limits, and warehouse staff who fulfill and ship orders. The platform exists because the previous fax-and-phone ordering process resulted in 15% order error rates and 3-day processing delays...",
                "domain_model": "The system centers around the Order entity, which progresses through a defined lifecycle: Draft -> Submitted -> Approved -> Fulfilled -> Shipped -> Delivered. Orders belong to a Customer (1:N relationship) and contain OrderLineItems (1:N). Each Customer has a CreditLimit entity that tracks available_credit, total_credit, and last_review_date...",
                "business_rules_catalog": [
                    {
                        "domain_area": "Authentication",
                        "rules": [
                            {
                                "rule_name": "login_lockout",
                                "trigger_condition": "3 consecutive failed login attempts within 15 minutes",
                                "action": "Lock account for 30 minutes, send email to account owner and security team",
                                "exceptions": "Admin accounts are never locked, only flagged",
                                "validation_logic": "Check failed_attempts >= 3 AND last_attempt_at > now() - 15min",
                            }
                        ],
                    }
                ],
                "technology_assessment": "The system runs on a Java 8 / Spring Boot 2.1 backend with a jQuery-based frontend. The PostgreSQL 10 database handles all persistence. Key strengths: mature codebase with good test coverage. Key weaknesses: Java 8 is EOL, Spring Boot 2.1 has known CVEs, jQuery frontend is difficult to maintain...",
                "user_workflows": [
                    {
                        "journey_name": "Place Order",
                        "actor": "Buyer",
                        "steps": [
                            "1. Login to portal",
                            "2. Search product catalog",
                            "3. Add items to cart",
                            "4. Review order total",
                            "5. Submit order for approval if over credit limit, else auto-approved",
                        ],
                        "business_rules_applied": ["credit_limit_check", "minimum_order_value"],
                    }
                ],
                "data_flow_description": "Orders enter the system through the web UI or EDI integration. On submission, the order is validated against the product catalog for pricing accuracy, then checked against the customer credit limit...",
                "integration_points": [
                    {
                        "system_name": "SAP ERP",
                        "integration_type": "API",
                        "description": "Real-time inventory sync via REST API",
                        "data_exchanged": ["inventory_levels", "product_catalog_updates"],
                    }
                ],
                "modernization_recommendations": [
                    {
                        "area": "Backend Framework",
                        "recommendation": "Upgrade to Spring Boot 3.x with Java 17",
                        "rationale": "Current Java 8 is EOL, missing security patches",
                        "trade_offs": "Requires updating all javax.* imports to jakarta.*, some Spring Security config changes",
                        "priority": "high",
                    }
                ],
            },
        },
    ]

    def get_required_skills(self) -> list[str]:
        return []  # Pure LLM synthesis task

    def validate(self, output: SystemUnderstanding) -> bool:
        """Ensure key sections have meaningful content."""
        if len(output.system_purpose) < 100:
            return False
        if len(output.domain_model) < 100:
            return False
        if not output.business_rules_catalog:
            return False
        return True
