import secrets
import string


def generate_password(length):
    all_characters = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(all_characters) for _ in range(length))
    return password
