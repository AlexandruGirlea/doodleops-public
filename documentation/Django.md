# How to Django

### How to generate a secret key
```bash
# build the web container
make build cont=web
# start the web container
make up cont=web
# generate a random secret key
make bash cont=web
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```