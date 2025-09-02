from app.models.lago.base_model import BaseListResponseModel, BaseResponseModel, LagoBaseModel
from app.models.lago.plan import PlanOverrides


class Subscription(LagoBaseModel):
    plan_code: str | None = None
    external_customer_id: str | None = None
    name: str | None = None
    external_id: str | None = None
    subscription_at: str | None = None
    billing_time: str | None = None
    ending_at: str | None = None
    plan_overrides: PlanOverrides | None = None


class SubscriptionResponse(BaseResponseModel):
    lago_id: str
    lago_customer_id: str | None = None
    external_customer_id: str | None = None
    canceled_at: str | None = None
    created_at: str | None = None
    plan_code: str | None = None
    started_at: str | None = None
    status: str | None = None
    name: str | None = None
    external_id: str | None = None
    billing_time: str | None = None
    terminated_at: str | None = None
    ending_at: str | None = None
    trial_ended_at: str | None = None
    subscription_date: str | None = None
    subscription_at: str | None = None
    previous_plan_code: str | None = None
    next_plan_code: str | None = None
    downgrade_plan_date: str | None = None
    current_billing_period_started_at: str | None = None
    current_billing_period_ending_at: str | None = None
    on_termination_credit_note: str | None = None
    on_termination_invoice: str | None = None


class SubscriptionsResponse(BaseListResponseModel[SubscriptionResponse]):
    root: list[SubscriptionResponse]
