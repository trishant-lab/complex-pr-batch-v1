from app.cli.temporal.core.log import log_info
from app.core.settings import AppSettings, get_settings, DexitAISettings, DexitAIEndpointSettings
from loguru import logger
from app.cli.temporal.dexit.dexit import DexitSpec
from huggingface_hub import get_inference_endpoint
from starlette.status import HTTP_409_CONFLICT
import aiohttp
from app.onepasswordutil import OnePasswordUtil
import asyncio


async def get_huggingface_endpoint_url(endpoint_name: str, check_interval: int = 10) -> str:
    """Resumes or waits for the HuggingFace inference endpoint based on its current status."""
    config: AppSettings = get_settings()
    endpoint = get_inference_endpoint(
        endpoint_name, token=config.dexit.ai_config.hf_token_write, namespace=config.dexit.ai_config.hf_username
    )
    # status -> 'running', 'paused', 'scaledToZero', 'pending', 'initializing'
    logger.info(f"endpoint status: {endpoint.status}")
    if endpoint.status in ("running", "scaledToZero"):
        logger.info(f"HuggingFace inference endpoint {endpoint_name} is in running state.")
        return endpoint.url
    else:
        if endpoint.status == "paused":
            logger.info(f"Resuming {endpoint_name} endpoint...")
            endpoint.resume()
        logger.info(f"Waiting for {endpoint_name} endpoint to be ready...")
        while endpoint.status != "running":
            if endpoint.status not in ("pending", "initializing"):
                logger.error(f"Failed to resume {endpoint_name} endpoint. Status: {endpoint.status}")
                raise Exception(f"Failed to resume {endpoint_name} endpoint. Status: {endpoint.status}")
            logger.debug(f"Waiting for {endpoint_name} to be up. Current status: {endpoint.status}")
            await asyncio.sleep(check_interval)
            endpoint = get_inference_endpoint(
                endpoint_name, token=config.dexit.ai_config.hf_token_read, namespace=config.dexit.ai_config.hf_username
            )
        logger.info(f"HuggingFace inference endpoint {endpoint_name} is in running state.")
        return endpoint.url


class HFInferenceEndpointSetup:
    def __init__(self: "HFInferenceEndpointSetup", dexit: DexitSpec) -> None:
        self.dexit: DexitSpec = dexit
        self.config: AppSettings = get_settings()
        self.ai_config: DexitAISettings = self.config.dexit.ai_config
        self.server_item = "production-config" if self.config.env == "production" else "integration-config"
        self.op_util = OnePasswordUtil(
            tenant=self.dexit.tenant,
            server_item=self.server_item,
            vault="Dexit",
        )
        self.op_util.insert_if_not_exists(key="ai_llm_entity_endpoint_name", value="")
        self.op_util.insert_if_not_exists(key="ai_llm_entity_endpoint_url", value="")
        self.op_util.insert_if_not_exists(key="ai_layoutlm_entity_endpoint_name", value="")
        self.op_util.insert_if_not_exists(key="ai_layoutlm_entity_endpoint_url", value="")
        self.op_util.insert_if_not_exists(key="ai_classification_endpoint_name", value="")
        self.op_util.insert_if_not_exists(key="ai_classification_endpoint_url", value="")
        self.op_util.insert_if_not_exists(key="ai_ocr_endpoint_name", value="")
        self.op_util.insert_if_not_exists(key="ai_ocr_endpoint_url", value="")

    async def create_endpoint(self: "HFInferenceEndpointSetup", endpoint: DexitAIEndpointSettings) -> None:
        """
        create endpoint
        """
        if not any(
            [
                endpoint.enable_ocr,
                endpoint.enable_classification,
                endpoint.enable_entity_llm,
                endpoint.enable_entity_layoutlm,
            ]
        ):
            logger.error("At least one of OCR, Classification or Entity Extraction should be enabled")
            raise ValueError("At least one of OCR, Classification or Entity Extraction should be enabled")

        headers = {"content-type": "application/json", "Authorization": f"Bearer {self.ai_config.hf_token_write}"}
        hf_url = f"https://api.endpoints.huggingface.cloud/v2/endpoint/{self.ai_config.hf_username}"

        endpoint_name = "dexit"
        if endpoint.enable_ocr:
            endpoint_name += "-ocr"
        if endpoint.enable_classification:
            endpoint_name += "-clf"
        if endpoint.enable_entity_layoutlm:
            endpoint_name += "-entlyt"
        if endpoint.enable_entity_llm:
            endpoint_name += "-entllm"
        endpoint_name += f"-{self.dexit.tenant}"
        endpoint_name = endpoint_name.lower().replace(" ", "-")[:32]

        payload = {
            # 'name' must not exceed 32 characters and should be in lowercase
            "name": endpoint_name,
            "compute": {
                "accelerator": endpoint.compute_engine.accelerator,
                "instanceSize": endpoint.compute_engine.instance_size,
                "instanceType": endpoint.compute_engine.instance_type,
                "scaling": {
                    "maxReplica": endpoint.compute_engine.max_replica,
                    "minReplica": endpoint.compute_engine.min_replica,
                    "scaleToZeroTimeout": endpoint.compute_engine.scale_to_zero_timeout,
                },
            },
            "provider": {"region": endpoint.compute_engine.region, "vendor": endpoint.compute_engine.vendor},
            "type": "protected",
            "model": {
                "framework": "custom",
                "image": {
                    "huggingface": {
                        "env": {
                            # ---------- OCR Related Configs ----------
                            "OCR_SERVICE_ENABLED": str(endpoint.enable_ocr),
                            "OCR_ENGINE": str(self.ai_config.ocr_engine.value),
                            # ---------- Entity Extraction (LLM) Related Configs ----------
                            "ENTITY_SERVICE_ENABLED_LLM": str(endpoint.enable_entity_llm),
                            "ENTITY_LLM_MODEL": str(self.ai_config.entity_llm_modelname.value),
                            "LLM_TEMPERATURE": str(self.ai_config.entity_llm_model_temperature),
                            "LLM_NUM_CTX": str(self.ai_config.entity_llm_model_numctx),
                            "LLM_NUM_PREDICT": str(self.ai_config.entity_llm_model_numpredict),
                            # ---------- Entity Extraction (LayoutLM) Related Configs ----------
                            "ENTITY_SERVICE_ENABLED_LAYOUTLM": str(endpoint.enable_entity_layoutlm),
                            "HF_LAYOUTLMV3_TOKEN_CLF_MODEL_ID": self.ai_config.entity_layoutlm_modelid,
                            "HF_LAYOUTLMV3_TOKEN_CLF_REVISION": self.ai_config.entity_layoutlm_modelrevision,
                            # ---------- Classification Related Configs ----------
                            "CLASSIFICATION_SERVICE_ENABLED": str(endpoint.enable_classification),
                            "HF_LAYOUTLMV3_SEQUENCE_CLF_MODEL_ID": self.ai_config.classification_modelid,
                            "HF_LAYOUTLMV3_SEQUENCE_CLF_REVISION": self.ai_config.classification_modelrevision,
                        }
                    }
                },
                "secrets": {
                    "HF_API_TOKEN_READ": self.ai_config.hf_token_read,
                },
                "repository": self.ai_config.hf_endpoint_repo_name,
                "revision": self.ai_config.hf_endpoint_repo_revision,
                "task": "custom",
            },
        }

        logger.info(f"Deploying HF Inference Endpoint {endpoint_name}")
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(hf_url, headers=headers, json=payload) as response:
                    if response.status == HTTP_409_CONFLICT:
                        logger.error(f"Endpoint {endpoint_name} already exists.")
                    logger.info(f"Response: {response.status}")
                    response.raise_for_status()  # Raises a HTTPError if the response status is 4xx, 5xx
                    logger.info(f"Endpoint {endpoint_name} creation has been submitted successfully to HF.")
            except aiohttp.ClientError as e:
                logger.exception(f"An error occurred while making the request: {e}")
            except Exception as e:
                logger.exception(f"An unexpected error occurred: {e}")

        endpoint_url = await get_huggingface_endpoint_url(endpoint_name, check_interval=30)

        log_info(f"Endpoint {endpoint_name} is ready at {endpoint_url}")

        op_util = OnePasswordUtil(
            tenant=self.dexit.tenant,
            server_item=self.server_item,
            vault="Dexit",
        )
        if endpoint.enable_entity_llm:
            op_util.create_or_replace(key="ai_llm_entity_endpoint_name", value=endpoint_name)
            op_util.create_or_replace(key="ai_llm_entity_endpoint_url", value=endpoint_url)
        if endpoint.enable_entity_layoutlm:
            op_util.create_or_replace(key="ai_layoutlm_entity_endpoint_name", value=endpoint_name)
            op_util.create_or_replace(key="ai_layoutlm_entity_endpoint_url", value=endpoint_url)
        if endpoint.enable_classification:
            op_util.create_or_replace(key="ai_classification_endpoint_name", value=endpoint_name)
            op_util.create_or_replace(key="ai_classification_endpoint_url", value=endpoint_url)
        if endpoint.enable_ocr:
            op_util.create_or_replace(key="ai_ocr_endpoint_name", value=endpoint_name)
            op_util.create_or_replace(key="ai_ocr_endpoint_url", value=endpoint_url)

    async def deploy(self: "HFInferenceEndpointSetup") -> None:
        """Deploy HF Inference Endpoints for tenant"""
        logger.info(f"Deploying HF Inference Endpoints for tenant {self.dexit.tenant}")
        endpoints: list[DexitAIEndpointSettings] = self.ai_config.inference_endpoints
        await asyncio.gather(*[self.create_endpoint(endpoint) for endpoint in endpoints])

    async def delete(self: "HFInferenceEndpointSetup") -> None:
        """Delete HF Inference Endpoints for tenant"""
        # logger.info(f"Deleting HF Inference Endpoints for tenant {self.dexit.tenant}")
        ...
