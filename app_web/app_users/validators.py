import phonenumbers
from django.core.exceptions import ValidationError


def validate_phone_number(value):
	"""Validate a phone number using the phonenumbers library."""
	try:
		# None -> no specific region
		parsed_number = phonenumbers.parse(value, None)
	except phonenumbers.NumberParseException:
		raise ValidationError("Invalid phone number format.")

	if not phonenumbers.is_valid_number(parsed_number):
		raise ValidationError("The phone number entered is not valid.")
