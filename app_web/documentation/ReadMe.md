# Documentation for Django-Web-Project DoodleOps

This directory contains documentation for App_Web DoodleOps.

### 1. For finding solutions to known problems, see the [Troubleshooting](troubleshooting.md) page.

If you encounter other problems and find a solution, please add it to the troubleshooting page.


### 2. How to run Celery commands in the terminal

```bash
# go inside the WEB docker container and run this
python manage.py shell
```

Example of python code

```python
# with no arguments
from app_financial.tasks import remove_credits_older_than_one_year
remove_credits_older_than_one_year.delay()

# with arguments
from app_api.tasks import has_api_counter_discrepancies

has_api_counter_discrepancies.delay("username")
```