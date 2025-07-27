import re
import string
import random

from cryptography.fernet import Fernet
from django.conf import settings

from common.exceptions import CustomValidationError

fernet_cipher = Fernet(settings.CRYPT_SECRET_KEY_WEB)

MIN_MAX_PASSWORD_LENGTH = (8, 100)


def encrypt_str(item: str) -> str:
    return fernet_cipher.encrypt(item.encode()).decode()


def decrypt_str(item: str) -> str:
    return fernet_cipher.decrypt(item.encode()).decode()


def generate_token():
    """
    Generate a random token using Fernet symmetric encryption key.
    """
    # Generate a random key
    key = Fernet.generate_key()

    return key.decode()


def validate_password(password1: str, password2: str) -> None:
    err_msg = "Password must contain at least one {}"
    errors = {}

    if password1 != password2:
        errors["password2"] = "Passwords do not match."

    if len(password1) < MIN_MAX_PASSWORD_LENGTH[0]:
        errors["password1"] = "Password must be at least 8 characters long."
    elif len(password1) > MIN_MAX_PASSWORD_LENGTH[1]:
        errors["password1"] = "Password must be at most 100 characters long."

    if not re.search("[a-z]", password1):
        errors["password1"] = err_msg.format("lowercase letter.")
    if not re.search("[A-Z]", password1):
        errors["password1"] = err_msg.format("uppercase letter.")
    if not re.search("[0-9]", password1):
        errors["password1"] = err_msg.format("number.")
    if not re.search('[!@#$%^&*(),.?":{}|<>]', password1):
        errors["password1"] = err_msg.format("special character.")

    if errors:
        raise CustomValidationError(dict_errors=errors)


def generate_strong_password(length=8):
    if length < 4:
        raise ValueError(
            "Password length should be at least 4 to accommodate each character "
            "class."
        )

    # Generate one character from each character class
    lowercase_char = random.choice(string.ascii_lowercase)
    uppercase_char = random.choice(string.ascii_uppercase)
    digit_char = random.choice(string.digits)
    special_char = random.choice('!@#$%^&*(),.?":{}|<>')

    # Generate the remaining characters randomly
    remaining_length = length - 4
    remaining_chars = "".join(
        random.choice(
            string.ascii_letters + string.digits + '!@#$%^&*(),.?":{}|<>'
        )
        for _ in range(remaining_length)
    )

    # Combine all the characters
    password = (
        lowercase_char
        + uppercase_char
        + digit_char
        + special_char
        + remaining_chars
    )

    # Shuffle the characters, so they aren't in a predictable order
    password = "".join(random.sample(password, len(password)))

    return password
