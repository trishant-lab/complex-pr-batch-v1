from functools import lru_cache

import lago_python_client
from pydantic import RedisDsn
from redis.asyncio import ConnectionPool, Redis

from app.core.settings import get_settings
from app.models.product import ProductEnum

settings = get_settings()


@lru_cache
def get_redis_conn() -> Redis:
    """
    @return:
    """
    kwargs = dict(host=settings.redis.host, port=settings.redis.port)
    if settings.redis.password:
        kwargs["password"] = settings.redis.password
    redis_dsn = RedisDsn.build(**kwargs, scheme="redis")
    pool = ConnectionPool.from_url(str(redis_dsn), max_connections=10)
    return Redis(connection_pool=pool)


@lru_cache
def get_lago_client(product: ProductEnum) -> lago_python_client.Client:
    """
    @return:
    """
    match product:
        case ProductEnum.veritable:
            lago_api_key = settings.veritable.lago.api_key
            lago_api_url = settings.veritable.lago.api_url
        case ProductEnum.zsegment:
            lago_api_key = settings.zsegment.lago.api_key
            lago_api_url = settings.zsegment.lago.api_url
        case ProductEnum.pricedx:
            lago_api_key = settings.pricedx.lago.api_key
            lago_api_url = settings.pricedx.lago.api_url
        case ProductEnum.dexit:
            lago_api_key = settings.dexit.lago.api_key
            lago_api_url = settings.dexit.lago.api_url
        case _:
            raise ValueError(f"Invalid product: {product}")

    return lago_python_client.Client(api_key=lago_api_key, api_url=lago_api_url)


@lru_cache
def get_lago_webhook_public_key(product: ProductEnum) -> bytes:
    """
    @return:
    """
    client = get_lago_client(product)

    return client.webhooks().public_key()
