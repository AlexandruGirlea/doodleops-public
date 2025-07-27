import json
from typing import List, Optional

from fastapi import HTTPException
from pydantic import (
	BaseModel, ValidationInfo, field_validator, ValidationError
)


MAX_VALUES_IN_LIST = 30
MAX_STRING_LENGTH = 1000


class FormData(BaseModel):
	remove_cell_values_same_row: Optional[List[str]] = None
	remove_cell_values_different_rows: Optional[List[str]] = None
	keep_cell_values_same_row: Optional[List[str]] = None
	keep_cell_values_different_rows: Optional[List[str]] = None
	sheet_name: Optional[str] = None
	columns: Optional[List[str]] = None

	@field_validator(
		"remove_cell_values_same_row", "remove_cell_values_different_rows",
		"keep_cell_values_same_row", "keep_cell_values_different_rows",
		mode='before'
	)
	@classmethod
	def validate_main_fields(
			cls, value: List[str], field: ValidationInfo
	):
		field = field.field_name
		if not value:
			return value
		elif not isinstance(value, list):
			raise ValueError(f"{field} must be a list")
		elif len(value) != len(set(value)):
			raise ValueError(f"Values in {field} must be unique")
		elif "--EMPTY--" in value and len(value) > 1:
			raise ValueError(
				f"'--EMPTY--' can only be provided as a single value in {field}."
			)
		elif len(value) > MAX_VALUES_IN_LIST:
			raise ValueError(
				f"Maximum {MAX_VALUES_IN_LIST} values are allowed in {field}."
			)
		elif any([i for i in value if len(i) > MAX_STRING_LENGTH]):
			raise ValueError(
				f"Maximum {MAX_STRING_LENGTH} characters are allowed in "
				f"a string in {field}."
			)

		if (
				field in (
				"remove_cell_values_same_row",
				"remove_cell_values_different_rows"
		)
		) and "--EMPTY--" in value and len(value) > 1:
			raise ValueError(
				f"'--EMPTY--' can only be provided as a single value in "
				f"{field}."
			)
		return value

	@field_validator('columns')
	def validate_columns(cls, v):
		if not v:
			return v
		elif len(v) != len(set(v)):
			raise ValueError("Values in columns must be unique")
		elif len(v) > MAX_VALUES_IN_LIST:
			raise ValueError(
				f"Maximum {MAX_VALUES_IN_LIST} values are allowed in columns."
			)
		return v

	@field_validator('sheet_name')
	def validate_sheet_name(cls, v):
		if not v:
			return v
		elif len(v) > 31:
			raise ValueError("Maximum 31 characters are allowed in sheet_name")
		return v


def validate_get_form_data(data: str) -> FormData:
	form_data = json.loads(data)
	try:
		return FormData(**form_data)
	except ValidationError as e:
		if len(e.errors()) > 1:
			errors = [i.get("msg") for i in e.errors()]
		else:
			errors = e.errors()[0].get("msg")
		raise HTTPException(status_code=400, detail=errors)