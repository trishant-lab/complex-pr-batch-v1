import uuid

from pydantic import EmailStr

from app.core.connections import get_redis_conn
from app.exceptions import errors
from app.models.product import ProductEnum
from app.route_utils.session_util import _get_hashed_key, generate_password


class UserSession:
    """
    Use Redis as session store
    """

    SESSION_TTL: int = 60 * 60  # 60 min
    MAX_RETRIES: int = 10

    @staticmethod
    async def create_session(product: ProductEnum, email: EmailStr) -> str:
        """
        Creates session token for user
        Returns the generated session token
        """
        conn = get_redis_conn()
        # Generate session token
        session_token = generate_password(50)
        key = _get_hashed_key(product, email, uuid.NAMESPACE_OID)
        # Store in Redis with TTL
        await conn.set(key, session_token, ex=UserSession.SESSION_TTL)
        return session_token

    @staticmethod
    async def get_session_token(product: ProductEnum, email: EmailStr) -> str:
        """
        Checks for valid session token if not creates a new one
        """
        conn = get_redis_conn()
        key = _get_hashed_key(product, email, uuid.NAMESPACE_OID)

        # Check if token exists
        existing_token = await conn.get(key)
        if existing_token:
            return existing_token.decode()

        # If no token exists, create new one
        return await UserSession.create_session(product, email)

    @staticmethod
    async def validate_session(product: ProductEnum, email: EmailStr, session_token: str) -> None:
        """
        Validates session token for user email
        Raises error if invalid or expired
        Maximum 10 retry attempts allowed
        """
        conn = get_redis_conn()
        key = _get_hashed_key(product, email, uuid.NAMESPACE_OID)

        async with conn.pipeline(transaction=True) as pipe:
            pipe = pipe.incr(key + "-c").mget(keys=[key, key + "-c"])
            stored_token, retry_count = (await pipe.execute())[-1]

        if stored_token is None:
            await conn.delete(key, key + "-c")
            raise errors.INVALID_OPERATION.exc()

        if session_token == stored_token.decode():
            await conn.delete(key + "-c")  # Only delete retry counter on success
        else:
            if int(retry_count) >= UserSession.MAX_RETRIES:
                await conn.delete(key, key + "-c")
                raise errors.INVALID_OPERATION.exc()
            raise errors.INVALID_OPERATION.exc()

    @staticmethod
    async def delete_session(product: ProductEnum, email: EmailStr) -> None:
        """
        Deletes session token for user email
        """
        conn = get_redis_conn()
        key = _get_hashed_key(product, email, uuid.NAMESPACE_OID)
        await conn.delete(key)

    @staticmethod
    async def refresh_session(product: ProductEnum, email: EmailStr, current_token: str) -> str:
        """
        Validates current session and issues a new session token
        Returns the new session token
        Raises error if current session is invalid
        """
        await UserSession.validate_session(product, email, current_token)

        conn = get_redis_conn()
        new_token = generate_password(50)
        key = _get_hashed_key(product, email, uuid.NAMESPACE_OID)

        # Update Redis with new token and reset TTL
        await conn.set(key, new_token, ex=UserSession.SESSION_TTL)

        # Reset retry counter
        await conn.delete(key + "-c")

        return new_token
