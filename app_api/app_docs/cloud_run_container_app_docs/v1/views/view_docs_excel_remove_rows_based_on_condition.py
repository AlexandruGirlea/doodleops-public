import os
import logging

import aiofiles
import pandas as pd
from pydantic import (
	BaseModel, ValidationInfo, field_validator, ValidationError
)
from fastapi import (
	APIRouter, File, UploadFile, HTTPException, BackgroundTasks, Depends, Form
)
from fastapi.responses import FileResponse

from views.urls import urls
from access_management.api_auth import verify_token
from utils.helper_methods import (
	cleanup_temp_dir, get_temp_file_path, validate_doc_file_input,
	excel_column_to_index, EXCEL_MEDIA_TYPE
)
from schemas.view_docs_excel_remove_rows_based_on_condition import (
	validate_get_form_data
)

logger = logging.getLogger(__name__)

docs_excel_remove_rows_based_on_condition_router = APIRouter(
	tags=["Excel"],
	responses={404: {"description": "Not found"}},
)


@docs_excel_remove_rows_based_on_condition_router.post(
	urls.get("excel").get("remove_rows_based_on_condition"),
	include_in_schema=True,
)
async def remove_rows_based_on_condition(
		background_tasks: BackgroundTasks,
		file: UploadFile = File(...),
		data: str = Form(...),
		token_data: bool = Depends(verify_token),
):
	"""
	`data` should be a JSON string because of limitations in HTTP and how
	browsers encode form data. The JSON string should be a dictionary
	with the following keys:\n

	```json
	{\n
		"remove_cell_values_same_row": ["value1", "value2"],\n
		"remove_cell_values_different_rows": ["value1", "value2"],\n
		"keep_cell_values_same_row": ["value2"],\n
		"keep_cell_values_different_rows": ["value1"],\n
		"sheet_name": "Sheet1",\n
		"columns": ["A", "B"]\n
	}
	```\n
	OBS 1: there are limitations in HTTP and how browser encodes form data, so the
	data should be a JSON string.\n\n

	`remove_cell_values_same_row` & `remove_cell_values_different_rows` &
	`keep_cell_values_same_row` & `keep_cell_values_different_rows`
	are mutually exclusive and at least one is needed to process the request.\n

	All values in the lists above should be unique.\n\n

	To remove rows that have at least one empty cell, provide `--EMPTY--` as a
	single value in `remove_cell_values_different_rows` optionally you can provide
	`columns` to specify the columns to check for empty cells.\n

	OBS 2: if `remove_cell_values_same_row` or `keep_cell_values_same_row` are
	provided, the `columns` key is not required, and it will be ignored.\n
	"""
	form_model = validate_get_form_data(data=data)

	validate_doc_file_input(file=file, file_extensions=('xlsx', 'xls'))

	remove_cell_values_same_row = form_model.remove_cell_values_same_row
	remove_cell_values_different_rows = form_model.remove_cell_values_different_rows
	keep_cell_values_same_row = form_model.keep_cell_values_same_row
	keep_cell_values_different_rows = form_model.keep_cell_values_different_rows
	sheet_name = form_model.sheet_name
	columns = form_model.columns

	main_filters = [
		remove_cell_values_same_row, remove_cell_values_different_rows,
		keep_cell_values_same_row, keep_cell_values_different_rows
	]

	if all([not i for i in main_filters]):
		raise HTTPException(
			status_code=400,
			detail=(
				"You must provide one of these: remove_cell_values_same_row, "
				"remove_cell_values_different_rows, "
				"keep_cell_values_same_row or keep_cell_values_different_rows"
			)
		)

	elif len([i for i in main_filters if i]) > 1:
		raise HTTPException(
			status_code=400,
			detail=(
				"Provide only one of remove_cell_values_same_row, "
				"remove_cell_values_different_rows, keep_cell_values_same_row "
				"or keep_cell_values_different_rows"
			)
		)

	column_indexes = []
	if columns:
		column_indexes = [excel_column_to_index(col_str=col) for col in columns]

	input_file_path = get_temp_file_path(extension='xlsx')
	temp_dir = os.path.dirname(input_file_path)

	try:
		async with aiofiles.open(input_file_path, 'wb') as input_file:
			content = await file.read()
			await input_file.write(content)

		try:
			data = pd.read_excel(
				input_file_path, keep_default_na=False, header=None, dtype=str,
				sheet_name=sheet_name
			)
		except ValueError as e:
			if (
					str(e).startswith("Worksheet named ") and
					str(e).endswith(" not found")
			):
				raise HTTPException(
					status_code=400,
					detail=(
						f"The sheet name '{sheet_name}' provided does not exist in "
						"the file."
					)
				)
			raise e
		except:
			raise HTTPException(
				status_code=400,
				detail="Could not read the file" if not sheet_name else (
					f"Could not read the file or the sheet name '{sheet_name}'."
				)
			)

		if not isinstance(data, pd.DataFrame) and len(data.keys()) > 1:
			raise HTTPException(
				status_code=400,
				detail=(
					"There are multiple sheets in the file. Please provide "
					"the sheet name"
				)
			)

		if isinstance(data, dict):
			if not data.keys():
				raise HTTPException(status_code=400, detail="The file is empty")
			data = data[list(data.keys())[0]]

		if not isinstance(data, pd.DataFrame):
			raise HTTPException(
				status_code=400,
				detail="Could not read the file"
			)

		if remove_cell_values_same_row:
			data = data[
				~data.apply(
					lambda row: all(
						value in row.values
						for value in remove_cell_values_same_row
					),
					axis=1
				)
			]
		elif keep_cell_values_same_row:
			data = data[
				data.apply(
					lambda row: all(
						value in row.values for value in keep_cell_values_same_row
					),
					axis=1
				)
			]

		if not remove_cell_values_same_row or not keep_cell_values_same_row:
			filtered_data = pd.DataFrame()
			for column_index in column_indexes:
				if (
						remove_cell_values_different_rows and
						"--EMPTY--" in remove_cell_values_different_rows
					):
					data = data[
						(data.iloc[:, column_index].notna()) &
						(data.iloc[:, column_index] != '')
						]
				elif remove_cell_values_different_rows:
					data = data[
						~data.iloc[:, column_index].isin(
							remove_cell_values_different_rows
						)
					]

				elif keep_cell_values_different_rows:
					filtered_data = pd.concat([
						filtered_data,
						data[
							data.iloc[:, column_index].isin(
								keep_cell_values_different_rows
							)
						]
					])

			if keep_cell_values_different_rows and column_indexes:
				data = filtered_data.drop_duplicates().sort_index()

			if not column_indexes:
				if remove_cell_values_different_rows:
					if "--EMPTY--" in remove_cell_values_different_rows:
						valid_rows = ((data != '') & data.notna()).all(axis=1)
						data = data[valid_rows]
					else:
						data = data[
							~data.isin(
								remove_cell_values_different_rows
							).any(axis=1)
						]
				elif keep_cell_values_different_rows:
					data = data[
						data.isin(keep_cell_values_different_rows).any(axis=1)
					]

		output_file_path = os.path.join(temp_dir, 'output.xlsx')

		data.to_excel(output_file_path, index=False, header=False)

		background_tasks.add_task(cleanup_temp_dir, temp_dir=temp_dir)
		return FileResponse(
			output_file_path,
			media_type=EXCEL_MEDIA_TYPE,
			filename='output.xlsx'
		)

	except (OSError, HTTPException, Exception) as e:
		logging.error(f"Error: {e}")
		cleanup_temp_dir(file_path=input_file_path)

		if isinstance(e, HTTPException):
			raise HTTPException(
				status_code=e.status_code,
				detail=e.detail
			)

		raise HTTPException(
			status_code=500,
			detail="Server error"
		)
