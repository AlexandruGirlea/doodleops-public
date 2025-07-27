import logging

from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class CustomRequestException(RequestException):
    def __init__(self, *args, http_status_code=None, **kwargs) -> None:
        # Initialize attributes
        self.http_status_code = http_status_code
        # Call the parent constructor with only positional arguments
        super().__init__(*args)



class CustomValidationError(Exception):
    def __init__(self, msg_error: str = None, dict_errors: dict = None) -> None:
        if not msg_error and not dict_errors:
            raise ValueError("You must pass either msg_error or dict_errors")
        super().__init__("There were validation errors.")
        self.msg_error = msg_error
        self.dict_errors = dict_errors
        logger.error(msg_error, dict_errors)
