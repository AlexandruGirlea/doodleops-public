import os
import sys

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# Add the app directory to the sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.fastapi_app import app


@pytest_asyncio.fixture
async def async_http_client():
	transport = ASGITransport(app=app)
	async with (
		AsyncClient(transport=transport, base_url="http://testserver") as client
	):
		yield client
