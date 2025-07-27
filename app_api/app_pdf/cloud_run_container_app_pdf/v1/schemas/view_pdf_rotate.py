import re
from typing import Optional

from pydantic import BaseModel, field_validator

# regex to check if string contains only digits and commas
DIGITS_COMMA_REGEX = r'^[\d,]+$'
MAX_CHAR_LENGTH = 500


class InputPDFRotate(BaseModel):
	pages_to_rotate_right: Optional[str] = None
	pages_to_rotate_left: Optional[str] = None
	pages_to_rotate_upside_down: Optional[str] = None

	@field_validator(
		'pages_to_rotate_right', 'pages_to_rotate_left',
		'pages_to_rotate_upside_down'
	)
	def check_pages_to_rotate(cls, v) -> Optional[list[int]]:
		if not v:
			return []

		if len(v) > MAX_CHAR_LENGTH:
			raise ValueError("Input too long.")

		v = v.replace(" ", "")

		# check regex
		if not re.match(DIGITS_COMMA_REGEX, v):
			raise ValueError("Invalid page numbers provided.")

		if not v.replace(',', '').isdigit():
			raise ValueError("Invalid page numbers provided.")

		try:
			values = [int(p) - 1 for p in v.split(',')]
		except ValueError:
			raise ValueError("Invalid page numbers provided.")

		return values
