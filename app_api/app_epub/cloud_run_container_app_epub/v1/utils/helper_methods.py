import uuid
import shutil


def get_random_file_name():
    return uuid.uuid4().hex


def get_unique_temp_dir():
    return f'/tmp/{uuid.uuid4().hex}'


def cleanup_temp_dir(temp_dir):
    """Function to clean up the temporary directory."""
    shutil.rmtree(temp_dir)
