from itertools import filterfalse

from better_profanity import profanity

from app.core.db import DBManager, get_db_manager
from app.models.billing_models import RESERVED_TENANT_NAMES
from app.models.product import ProductEnum


def _is_valid_suggestion(prefix: str) -> bool:
    """
    Checks if the prefix is a valid suggestion.
    """
    return (
        2 < len(prefix) <= 15
        and prefix.lower() not in RESERVED_TENANT_NAMES
        and not profanity.contains_profanity(prefix.lower())
    )


def _is_digit_prefix(prefix: str, word_part: str) -> bool:
    """
    Checks if the prefix or the word part is a digit prefix.
    """
    return prefix.isdigit() or (prefix == "" and word_part.isdigit())


def _name_suggestions_helper(prefix: str, start: int, combinations: set[str], words: list[str]) -> None:
    """
    Adds valid name suggestions to the combinations set.
    """
    if len(combinations) > 20:
        return
    if start >= len(words):
        if _is_valid_suggestion(prefix):
            combinations.add(prefix.lower())
    else:
        word = words[start]
        for j in range(1, len(word) + 1):
            if _is_digit_prefix(prefix, word[:j]):
                continue

            new_prefix = prefix + (
                "".join(x for x in word[:j] if x.isalpha())
                if prefix == ""
                else "".join(x for x in word[:j] if x.isalnum())
            )

            _name_suggestions_helper(new_prefix, start + 1, combinations, words)

        if not combinations:
            _name_suggestions_helper(prefix, start + 1, combinations, words)


def generate_combinations(organization: str) -> list:
    """
    @param organization:
    @return:
    """
    filtered_name = "".join(y for y in organization if y.isalpha() or y.isdigit() or y.isspace())
    words = filtered_name.split()
    combinations = set()

    _name_suggestions_helper("", 0, combinations, words)
    return sorted(combinations, key=len)


async def get_valid_suggestions(product: ProductEnum, email: str, organization: str) -> list:
    """
    @param email:
    @param organization:
    @return:
    """
    combinations = generate_combinations(organization)
    existing_tenants = await get_existing_tenant_names(product=product, email=email, tenant_names=combinations)
    return list(filterfalse(existing_tenants.__contains__, combinations))


async def get_existing_tenant_names(product: ProductEnum, email: str | None, tenant_names: list) -> list:
    """
    @param product:
    @param tenant_names:
    @return:
    """
    if not tenant_names:
        return []

    params = {
        "tenant_names": tenant_names,
        "product": product.value,
    } | ({"email": email} if email else {})
    db: DBManager = await get_db_manager()
    return [data["tenantname"] for data in await db.fetch_all("get_valid_tenant_names.sql", **params)]
