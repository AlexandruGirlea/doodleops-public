# APP API


## 0. Install the necessary python version

Mac OS setup:
```bash
brew install pyenv
brew install pyenv-virtualenv
pyenv install 3.10
pyenv global 3.10

nano ~/.zshrc
# add this to the end of the file
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv virtualenv-init -)"

source ~/.zshrc
```

## 1. How the API services are structured:

- each microservice has its own folder that starts with `app_` prefix.
- we can have up to two sub-folders inside each service folder:
    - OPTIONAL: `cloud_run_container_{NAME_OF_SERVICE}` - this is the Docker 
  Container service that will be deployed to Google Cloud Run. This is optional 
  because not all views require a Cloud Run service, some may use external paid 
  services.
    - MANDATORY: `views` - contains the actual FastAPI views that are used by the
  Clients for direct API access and by the internal Django Web App.

OBS: All API views in `cloud_run_container` folder should be implemented in the
`views` folder as well, but the opposite is not true. The `views` folder can have
views that are not implemented in the `cloud_run_container` folder because they
might be external services that are paid.

### 2. How to run the API services locally:
Use the Makefile to run the API services locally. You need to:
- build the Docker container (`make build cont=....`)
- run the Docker container (`make up cont=....`)
- run the FastAPI server (`make run cont=....`)


### 3. How to manage API URLS and feature toggles:

In `core.settings` we have `CLOUD_RUN_APPs`, that is a dict with all the Cloud Run
services that are available. Each service has a `base_url` that points to the
Cloud Run service URL.

In `core.urls` we have the `urls` that is a dict of API endpoints that are 
available. Each endpoint has one or more version keys (ex: `v1`) and each version
has a dict with a key (name) and a value of one of these object types:
- `CloudRunAPIEndpoint`
- `ExternalAPIEndpoint`

We use the above object types to define the API endpoints inside our Views.

There is also a middleware in `core.fastapi_app` that checks if the API endpoint
is enabled or not (`check_api_toggle`). If the API endpoint is disabled, it will
not be part of the `allowed_endpoints`, and it will return a 403 error.

## How to generate API keys for requests

```bash
python -c "from cryptography.fernet import Fernet; \

EXPECTED=Fernet.generate_key(); \
print('\n', '\nEXPECTED=', EXPECTED.decode()); \
CRYPT_SECRET_KEY_G_CLOUD_RUN = Fernet.generate_key(); \
print('CRYPT_SECRET_KEY_G_CLOUD_RUN=',CRYPT_SECRET_KEY_G_CLOUD_RUN.decode(), '\n', '\n'); \

fernet_cipher = Fernet(CRYPT_SECRET_KEY_G_CLOUD_RUN); \
print(fernet_cipher.encrypt(EXPECTED).decode())"
```