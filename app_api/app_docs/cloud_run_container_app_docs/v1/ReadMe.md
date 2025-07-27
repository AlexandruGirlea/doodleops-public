## How to run tests for app_docs_v1 microservice

0. Build / Start the container and run the server
```bash
make build cont=app_docs_v1
make up cont=app_docs_v1
make run cont=app_docs_v1
```

1. In another terminal while the above server is running, go inside the container
```bash
make bash cont=app_docs_v1
```

2. Install the python libraries needed for testing
```bash
pip install pytest httpx pytest-asyncio
```

3Run the following command (inside the container) to run the tests:
```bash
OTEL_SDK_DISABLED=true pytest -q
```