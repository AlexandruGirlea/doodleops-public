import random
import string


def generate_strong_password(length=8):
    """
    First we generate at least one character from each character class.
    Then we generate the remaining characters randomly.
    Finally we shuffle the characters, so they aren't in a predictable order.
    """
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

    print(password)


if __name__ == "__main__":
    length = int(input("Enter password length: "))
    generate_strong_password(length=length)
