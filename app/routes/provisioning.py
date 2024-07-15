import datetime
import re
import uuid
from typing import TYPE_CHECKING

import orjson
import requests
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from loguru import logger
from pydantic import ValidationError, BaseModel
from starlette.requests import Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR, HTTP_400_BAD_REQUEST
from temporalio.client import WorkflowHandle

from .product import get_product
from .tenant import create_tenant, TenantCreateRequestModel
from ..core.db import get_db_manager, DBManager
from ..core.oauth2 import get_oauth_scheme
from ..core.settings import get_settings, AppSettings
from ..models.product import ProductEnum
from ..models.tenant import TenantStatusEnum
from ..slack_utils import send_slack_msg

provisioning_router = APIRouter()


if TYPE_CHECKING:
    from ..cli.workflowbase import ProductWorkflow


async def send_slack_notification(product: ProductEnum, schema: dict, approval_required: bool, tenant_id: str) -> None:
    """
    Send Slack notification
    """
    config: AppSettings = get_settings()
    text = (
        f"A new {product.value} tenant has been requested by "
        f"{schema.get('email')} from {schema.get('organization')}"
    )
    blocks = [
        {"type": "divider"},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": text,
            },
        },
        {
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"*TenantName:* {schema['tenant']}",
                }
            ],
        },
    ]
    if approval_required:
        extended_block = [
            {
                "type": "section",
                "fields": [{"type": "mrkdwn", "text": "*Approval Required:*"}],
            },
            {
                "type": "rich_text",
                "elements": [
                    {
                        "type": "rich_text_section",
                        "elements": [
                            {
                                "type": "link",
                                "url": f"{config.app_url}/tenant-details?id={tenant_id}",
                            }
                        ],
                    }
                ],
            },
        ]
        blocks.extend(extended_block)

    blocks.append({"type": "divider"})

    send_slack_msg(text=text, blocks=blocks)


@provisioning_router.post(
    "",
    operation_id="provisioning",
)
async def provisioning(
    product: ProductEnum,
    schema: dict,
    request: Request,
    skip_approval: bool = False,
    _param: dict = Depends(get_oauth_scheme()),
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> None:
    """
    Trigger provisioning workflow for the given product
    """
    try:
        schema["tenant"] = schema.get("tenantName") if schema.get("tenantName") else schema.get("tenant")
        product_model = ProductEnum.get_input_model_class(product)
        product_model.model_validate(schema)
    except ValidationError as e:
        logger.error(f"Invalid schema: {e.errors()}")
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Invalid schema")

    user_id: dict = request.scope.get("user", {}).get("sub")
    product_details = await get_product(product=product, _param=_param)
    if not product_details:
        raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail="Product not found")
    product_details = dict(product_details)

    # Create tenant
    tenant_details = await create_tenant(
        TenantCreateRequestModel(
            name=schema.get("tenant"),
            product=product_details["id"],
            status=TenantStatusEnum.Provisioning
            if product_details["approvalRequired"] and skip_approval
            else TenantStatusEnum.PendingApproval,
            requestor={
                "userName": f"{schema.get('firstName')} {schema.get('lastName')}",
                "email": schema.get("email"),
                "organization": schema.get("organization"),
                "contactNumber": schema.get("contactNumber"),
            },
            approvedBy=user_id if skip_approval else None,
            schema_=orjson.dumps(schema).decode("utf-8"),
        ),
        _param=_param,
    )

    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
    await product_workflow.onboard(schema)
    logger.info(f"Triggered provisioning workflow for product: {product.value}")

    background_tasks.add_task(
        send_slack_notification,
        product=product,
        schema=schema,
        approval_required=True if product_details["approvalRequired"] and not skip_approval else False,
        tenant_id=tenant_details.get("id"),
    )

    if product_details["approvalRequired"] and skip_approval:
        logger.info(f"Skipping approval for product: {product.value}")
        await product_workflow.approve(schema)


@provisioning_router.post("/approveOrDecline", operation_id="approveOrDecline")
async def approve_tenant(
    product: ProductEnum,
    approval: bool,
    tenant_id: uuid.UUID,
    request: Request,
    _param: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    Approve tenant
    """
    config: AppSettings = get_settings()
    user_id: dict = request.scope.get("user", {}).get("sub")
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getTenant.sql", tenant_id=str(tenant_id))
        await db.fetch_one(
            "approveTenant.sql",
            tenant_id=str(tenant_id),
            user_id=user_id,
            status=TenantStatusEnum.Provisioning if approval else TenantStatusEnum.Declined,
        )

    except Exception as e:
        logger.error(f"Error approving tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error approving tenant")

    schema = orjson.loads(response["schema"])
    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()

    if approval:
        await product_workflow.approve(schema)
        logger.info(f"Approved {response['product_name']} workflow for tenant: {response['name']}")
    else:
        await product_workflow.decline(schema)
        logger.info(f"Declined {response['product_name']} workflow for tenant: {response['name']}")


@provisioning_router.post("/retryProvisioning", operation_id="retryProvisioning")
async def retry_provisioning(
    product: ProductEnum,
    tenant_id: uuid.UUID,
    _param: dict = Depends(get_oauth_scheme()),
) -> None:
    """
    Retry provisioning
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getTenant.sql", tenant_id=str(tenant_id))
        await db.fetch_one(
            "updateTenant.sql",
            tenant_name=response["name"],
            status=TenantStatusEnum.Provisioning.value,
            product=product.value,
        )
        schema = orjson.loads(response["schema"])
        product_workflow: ProductWorkflow = ProductEnum.get_class(product)()
        await product_workflow.onboard(schema)

        # await product_workflow.approve(schema)
        logger.info(f"Retried provisioning workflow for tenant: {response['name']}")
    except Exception as e:
        logger.error(f"Error retrying provisioning: {e}")
        raise HTTPException(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrying provisioning",
        )


class Logs(BaseModel):
    loglevel: str
    log: str


class WorkflowSteps(BaseModel):
    activityName: str
    status: str
    logs: list[Logs]


async def get_grafana_logs(config: AppSettings, workflow_id: str, from_: datetime.datetime) -> dict:
    """
    Get Grafana logs
    """
    url = f"{config.grafana_url}/api/ds/query"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config.grafana_token}"}
    expr = f'{{name="launchpad_custom_logs"}} |= `workflow_id={workflow_id}` | json'

    from_ = int(from_.timestamp()) * 1000
    to_ = int(datetime.datetime.now().timestamp()) * 1000

    payload = orjson.dumps(
        {
            "queries": [
                {
                    "expr": expr,
                    "queryType": "range",
                    "refId": "loki-data-samples",
                    "maxLines": 5000,
                    "supportingQueryType": "dataSample",
                    "legendFormat": "",
                    "datasource": {"type": "loki", "uid": "e4hhV8CGk"},
                    "datasourceId": 2,
                    "intervalMs": 10800000,
                }
            ],
            "from": str(from_),
            "to": str(to_),
        }
    ).decode()

    response = requests.request("POST", url, headers=headers, data=payload)

    response.raise_for_status()

    logs = {}
    for log in response.json()["results"]["loki-data-samples"]["frames"][0]["data"]["values"][0]:
        loglevel_match = re.search(r"loglevel=(\w+)", log["message"])
        activity_log = re.search(r"activity_name:[^ ]+ (.+)", log["message"])
        activity_name = re.search(r"activity_name:([^ ]+)", log["message"])

        loglevel = loglevel_match.group(1) if loglevel_match else None
        activity_name_ = activity_name.group(1) if activity_name else None
        activity_log_ = activity_log.group(1).strip().replace('"', "") if activity_log else None

        if activity_name_ in logs:
            logs[activity_name_].append({"loglevel": loglevel, "log": activity_log_})
        else:
            logs[activity_name_] = [{"loglevel": loglevel, "log": activity_log_}]
    return logs


@provisioning_router.get("/workflowSteps", operation_id="workflowSteps")
async def get_workflow_steps(
    product: ProductEnum,
    tenant_id: uuid.UUID,
    _param: dict = Depends(get_oauth_scheme()),
) -> list[WorkflowSteps]:
    """
    Get workflow steps and logs
    """
    config: AppSettings = get_settings()
    try:
        db: DBManager = await get_db_manager(config.postgres.dsn)
        response = await db.fetch_one("getTenant.sql", tenant_id=str(tenant_id))
        schema = orjson.loads(response["schema"])
    except Exception as e:
        logger.error(f"Error fetching tenant: {e}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching tenant")

    product_workflow: ProductWorkflow = ProductEnum.get_class(product)()

    workflow_handle: WorkflowHandle = await product_workflow.get_workflow_handle(schema=schema)

    history = await workflow_handle.fetch_history()

    workflow_steps = {}
    for event in history.to_json_dict()["events"]:
        if event["eventType"] in ["EVENT_TYPE_ACTIVITY_TASK_SCHEDULED"]:
            workflow_steps[event["eventId"]] = {
                "activityName": event["activityTaskScheduledEventAttributes"]["activityType"]["name"],
                "status": "scheduled",
            }

        if event["eventType"] in ["EVENT_TYPE_ACTIVITY_TASK_STARTED"]:
            workflow_steps.get(event["activityTaskStartedEventAttributes"]["scheduledEventId"]).update(
                {"status": "started"}
            )
        if event["eventType"] in ["EVENT_TYPE_ACTIVITY_TASK_COMPLETED"]:
            workflow_steps.get(event["activityTaskCompletedEventAttributes"]["scheduledEventId"]).update(
                {"status": "completed"}
            )

    logs = await get_grafana_logs(config, workflow_id=workflow_handle.id, from_=response.get("created"))

    [activity.update({"logs": logs.get(activity["activityName"], [])}) for activity in workflow_steps.values()]

    return [WorkflowSteps(**activity) for activity in workflow_steps.values()]
