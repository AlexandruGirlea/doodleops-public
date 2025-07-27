import os
import json
import tempfile
import itertools

import pytest
from httpx import Response, AsyncClient
import pandas as pd

from views.urls import urls
from tests import async_http_client

url = urls["excel"]["remove_rows_based_on_condition"]

CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
input_excel_path = (
	"tests/fixtures/test_view_docs_excel_remove_rows_based_on_condition.xlsx"
)


def generic_response_test(response: Response):
	assert response.status_code == 200
	assert response.headers["Content-Type"] == CONTENT_TYPE
	assert response.headers["Content-Disposition"] == (
		'attachment; filename="output.xlsx"'
	)


def generic_load_excel_from_path_test(path: str):
	try:
		return pd.read_excel(path, keep_default_na=False, header=None, dtype=str)
	finally:
		if os.path.exists(path):
			os.remove(path)


async def make_post_request(async_http_client: AsyncClient, data: dict):
	with open(input_excel_path, 'rb') as file:
		return await async_http_client.post(
			url,
			files={'file': (input_excel_path, file, CONTENT_TYPE)},
			data={'data': json.dumps(data)}
		)


def write_to_temp_file(response: Response) -> str:
	with tempfile.NamedTemporaryFile(delete=False) as temp_file:
		temp_file.write(response.content)
		return temp_file.name


@pytest.mark.asyncio
async def test_remove_all_rows_with_empty_cells(async_http_client):
	data = {
		"remove_cell_values_different_rows": ["--EMPTY--"],
		"sheet_name": "Sheet 1",
	}

	response = await make_post_request(async_http_client, data)
	generic_response_test(response=response)
	temp_file_path = write_to_temp_file(response)
	df = generic_load_excel_from_path_test(path=temp_file_path)

	assert not df.isna().any().any(), "The DataFrame contains NaN values."
	assert len(df) == 19, "The DataFrame has the wrong number of rows."


@pytest.mark.asyncio
async def test_remove_all_rows_with_empty_cells_from_column(async_http_client):
	data = {
		"remove_cell_values_different_rows": ["--EMPTY--"],
		"sheet_name": "Sheet 1",
		"columns": ["B", ]
	}

	response = await make_post_request(async_http_client, data)
	generic_response_test(response=response)
	temp_file_path = write_to_temp_file(response)
	df = generic_load_excel_from_path_test(path=temp_file_path)

	assert len(df) == 20, "The DataFrame has the wrong number of rows."


@pytest.mark.asyncio
async def test_remove_cell_values_different_rows_from_column(async_http_client):
	data = {
		"remove_cell_values_different_rows": ["A"],
		"sheet_name": "Sheet 1",
		"columns": ["A", ]
	}

	response = await make_post_request(async_http_client, data)
	generic_response_test(response=response)
	temp_file_path = write_to_temp_file(response)
	df = generic_load_excel_from_path_test(path=temp_file_path)
	assert not df.isin(["A"]).any().any(), (
		"DataFrame does not contain 'A' values."
	)
	assert len(df) == 11, "The DataFrame has the wrong number of rows."


@pytest.mark.asyncio
async def test_remove_cell_values_different_rows(async_http_client):
	values = ["15", "20", "l", "m"]
	data = {
		"remove_cell_values_different_rows": values,
		"sheet_name": "Sheet 1",
	}

	response = await make_post_request(async_http_client, data)
	generic_response_test(response=response)
	temp_file_path = write_to_temp_file(response)
	df = generic_load_excel_from_path_test(path=temp_file_path)

	assert not df.isin(values).any().any(), (
		f"The DataFrame contains {values} values."
	)
	assert len(df) == 17, "The DataFrame has the wrong number of rows."


@pytest.mark.asyncio
async def test_remove_cell_values_same_row(async_http_client):
	values = ["b", "2"]
	data = {
		"remove_cell_values_same_row": values,
		"sheet_name": "Sheet 1",
	}
	response = await make_post_request(async_http_client, data)
	generic_response_test(response=response)
	temp_file_path = write_to_temp_file(response)
	df = generic_load_excel_from_path_test(path=temp_file_path)

	assert not df.isin(values).any().any(), (
		f"The DataFrame contains {values} values in the same row."
	)
	assert len(df) == 20, "The DataFrame has the wrong number of rows."


@pytest.mark.asyncio
async def test_keep_cell_values_same_row(async_http_client):
	values = ["a", "1"]
	data = {
		"keep_cell_values_same_row": values,
		"sheet_name": "Sheet 1",
	}
	response = await make_post_request(async_http_client, data)
	generic_response_test(response=response)
	temp_file_path = write_to_temp_file(response)
	df = generic_load_excel_from_path_test(path=temp_file_path)

	assert df.isin(values).any().any(), (
		f"DataFrame does not contain {values} values."
	)
	assert df.isin(values).any().any(), (
		f"DataFrame does not contain {values} values."
	)
	assert len(df) == 1, "The DataFrame has the wrong number of rows."


@pytest.mark.asyncio
async def test_keep_cell_values_different_rows(async_http_client):
	data = {
		"keep_cell_values_different_rows": ["a", "j", "10"],
		"sheet_name": "Sheet 1",
		"columns": ["B", "C"]
	}

	response = await make_post_request(async_http_client, data)
	generic_response_test(response=response)
	temp_file_path = write_to_temp_file(response)
	df = generic_load_excel_from_path_test(path=temp_file_path)

	assert df.isin(["a", "j", "10"]).any().any(), (
		"DataFrame does not contain 'a', 'b', or '10' values."
	)
	assert len(df) == 2, "The DataFrame has the wrong number of rows."


@pytest.mark.asyncio
async def test_raise_mutually_exclusive_error(async_http_client):
	keys = [
		'remove_cell_values_same_row', 'remove_cell_values_different_rows',
		'keep_cell_values_same_row', 'keep_cell_values_different_rows'
	]
	all_combinations = [
		list(comb) for i in range(2, 5)
		for comb in itertools.combinations(keys, i)
	]

	for c in all_combinations:
		data = {
			"sheet_name": "Sheet 1",
			"columns": ["A", "B"]
		}
		data.update({k: ["--EMPTY--"] for k in c})

		response = await make_post_request(async_http_client, data)
		assert response.status_code == 400
		assert "Provide only one" in response.json().get("detail")


@pytest.mark.asyncio
async def test_missing_required_param_error(async_http_client):
	data = {
		"columns": ["A", "B"]
	}

	response = await make_post_request(async_http_client, data)
	assert response.status_code == 400
	assert "You must provide one of these:" in response.json().get("detail")


@pytest.mark.asyncio
async def test_missing_sheet_name_error(async_http_client):
	sheet_name = "Non Existent Sheet"
	data = {
		"remove_cell_values_same_row": ["--EMPTY--"],
		"sheet_name": sheet_name,
		"columns": ["A", "B"]
	}

	response = await make_post_request(async_http_client, data)
	assert response.status_code == 400
	assert (
			f"The sheet name '{sheet_name}' provided does not exist in" in
			response.json().get("detail")
	)


@pytest.mark.asyncio
async def test_raise_uniqueness_error(async_http_client):
	keys = [
		'remove_cell_values_same_row', 'remove_cell_values_different_rows',
		'keep_cell_values_same_row', 'keep_cell_values_different_rows'
	]

	for k in keys:
		data = {
			k: ["value1", "value1"],
			"sheet_name": "Sheet 1",
			"columns": ["A", "B"]
		}

		response = await make_post_request(async_http_client, data)
		assert response.status_code == 400
		assert (
				f"Values in {k} must be unique" in
				response.json().get("detail")
		)


@pytest.mark.asyncio
async def test_raise_input_validation_type_errors(async_http_client):
	keys = [
		'remove_cell_values_same_row', 'remove_cell_values_different_rows',
		'keep_cell_values_same_row', 'keep_cell_values_different_rows'
	]
	for k in keys:
		data = {
			k: 1,
			"sheet_name": "Sheet 1",
			"columns": ["A", "B"]
		}

		response = await make_post_request(async_http_client, data)
		assert response.status_code == 400
		assert f"{k} must be a list" in response.json().get("detail")

	data = {
		"remove_cell_values_same_row": ["value"],
		"sheet_name": 1,
		"columns": ["A", "B"]
	}

	response = await make_post_request(async_http_client, data)
	assert response.status_code == 400
	assert "Input should be a valid string" in response.json().get("detail")

	data = {
		"remove_cell_values_same_row": ["value"],
		"sheet_name": "Sheet 1",
		"columns": "A"
	}

	response = await make_post_request(async_http_client, data)
	assert response.status_code == 400
	assert 'Input should be a valid list' in response.json().get("detail")

	for k in keys + ["columns"]:
		data = {
			k: [f"value_{n}" for n in range(31)],
			"sheet_name": "Sheet 1",
		}
		if k == "columns":
			data["keep_cell_values_same_row"] = ["A", "B"]

		response = await make_post_request(async_http_client, data)
		assert response.status_code == 400
		assert f"Maximum 30 values are allowed in {k}." in (
			response.json().get("detail")
		)

	for k in keys:
		data = {
			k: ["a" * 1001],
			"sheet_name": "Sheet 1",
		}

		response = await make_post_request(async_http_client, data)
		assert response.status_code == 400
		assert (
				f"Maximum 1000 characters are allowed in a string in {k}." in
				response.json().get("detail")
		)

	data = {
		"remove_cell_values_same_row": ["value1", "value2"],
		"sheet_name": "a"*32,
		"columns": ["A", "B"]
	}
	response = await make_post_request(async_http_client, data)
	assert response.status_code == 400
	assert (
			"Maximum 31 characters are allowed in sheet_name" in
			response.json().get("detail")
	)

	for c in (["A1"], ["XFE"], ["ABCD"]):
		data = {
			"remove_cell_values_same_row": ["value1", "value2"],
			"sheet_name": "a",
			"columns": c
		}
		response = await make_post_request(async_http_client, data)
		assert response.status_code == 400
		if not c[0].isalpha():
			error = "Column string must consist of letters only."
		else:
			error = "Column string out of Excel's limits (A to XFD)."

		assert error in response.json().get("detail")
