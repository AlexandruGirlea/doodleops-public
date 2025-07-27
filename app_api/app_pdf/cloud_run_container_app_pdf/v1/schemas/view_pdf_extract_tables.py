from typing import List
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator, Field


class FlavorEnum(Enum):
	lattice = "lattice"
	stream = "stream"


class OutputOptions(Enum):
	one_excel = "one_excel"  # multiple sheets
	multiple_excels = "multiple_excels"


class OutputFormat(Enum):
	excel = "excel"
	csv = "csv"


class Payload(BaseModel):
	pages: Optional[str] = Field(
		"all",
		description=(
			"Specify the pages to process, e.g., '1,3,4'. Default is 'all'."
		)
	)
	table_areas: Optional[List[str]] = Field(
		None, description="List of coordinates specifying table areas to extract."
	)
	flavor: Optional[FlavorEnum] = FlavorEnum.lattice.value
	scale: Optional[int] = 15
	process_background: Optional[bool] = False
	backend: Optional[str] = "ghostscript"
	output_format: Optional[OutputFormat] = OutputFormat.excel
	output_options: Optional[OutputOptions] = OutputOptions.multiple_excels

	@field_validator("pages")
	def validate_pages(cls, value):
		if value == "all":
			return value
		if value and not value.replace(",", "").isdigit():
			raise ValueError("Invalid page numbers")
		return value

	@field_validator("table_areas")
	def validate_table_areas(cls, value):
		if value and not all([area.replace(",", "").isdigit() for area in value]):
			raise ValueError("Invalid table areas")
		return value

	@field_validator("scale")
	def validate_scale(cls, value):
		if not 1 <= value <= 100:
			raise ValueError("Invalid scale factor")
		return value

	@field_validator("backend")
	def validate_backend(cls, value):
		if not value:
			return "poppler"
		if value not in ["poppler", "ghostscript"]:
			raise ValueError("Invalid backend")
		return value
