import cgi
import uuid
import json
import shutil
import string
import random
import urllib.parse


def generate_random_chars(length: int = 5) -> str:
	# Define the characters that can be used in the string
	characters = string.ascii_letters + string.digits
	# Generate a random string of the specified length
	return "".join(random.choice(characters) for _ in range(length))


def load_api_config() -> dict:
	with open("access_management/api_urls_config.json", "r") as file:
		api_urls_config = json.load(file)
		for k in list(api_urls_config.keys()):
			if k.startswith("_"):
				api_urls_config.pop(k, None)

	return api_urls_config


def get_unique_temp_dir() -> str:
	return f'/tmp/{uuid.uuid4().hex}'


def cleanup_temp_dir(temp_dir: str) -> None:
	"""Function to cleanup the temporary directory."""
	shutil.rmtree(temp_dir)


def generate_unique_filename(extension: str = None) -> str:
	return f"{uuid.uuid4()}{extension}"


def get_filename_from_cd(headers: dict) -> str:
	"""
	Extract a filename from Content-Disposition, handling both
	`filename=` and `filename*=` (RFC 5987) formats.
	"""
	content_disposition = headers.get("content-disposition", "")
	_, params = cgi.parse_header(content_disposition)

	filename = params.get('filename')
	if filename:
		return filename

	filename_star = params.get('filename*')
	if filename_star:
		parts = filename_star.split("''", 1)
		if len(parts) == 2:
			_, encoded_filename = parts
			return urllib.parse.unquote(encoded_filename)
		else:
			return urllib.parse.unquote(filename_star)

	return ""


def clean_openapi_schemas(openapi_schema: dict, filtered_paths: dict) -> dict:
	# If there are no components, just return now
	if (
			"components" not in openapi_schema or
			"schemas" not in openapi_schema["components"]
	):
		return openapi_schema

	all_schemas = openapi_schema["components"]["schemas"]

	def find_refs(obj, found_refs):
		if isinstance(obj, dict):
			for key, value in obj.items():
				if key == "$ref" and isinstance(value, str) and value.startswith(
						"#/components/schemas/"):
					schema_name = value.split("/")[-1]
					if schema_name not in found_refs:
						found_refs.add(schema_name)
						# Recursively also find references within that schema
						if schema_name in all_schemas:
							find_refs(all_schemas[schema_name], found_refs)
				else:
					find_refs(value, found_refs)
		elif isinstance(obj, list):
			for item in obj:
				find_refs(item, found_refs)

	# Collect the necessary schemas
	needed_schemas = set()
	# Iterate over all filtered paths and methods, extracting refs
	for path, methods in filtered_paths.items():
		for http_method, operation in methods.items():
			find_refs(operation, needed_schemas)

	# Prune the schemas not in needed_schemas
	pruned_schemas = {
		name: schema
		for name, schema in all_schemas.items()
		if name in needed_schemas
	}

	return pruned_schemas
