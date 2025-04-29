import secrets
import string


def generate_password(length: int) -> str:
    """
    :param length:
    :return:
    """
    all_characters = string.ascii_letters + string.digits
    return "".join(secrets.choice(all_characters) for _ in range(length))
