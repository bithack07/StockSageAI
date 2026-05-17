import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_register_rejects_weak_password():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/auth/register",
            json={"email": "weak@example.com", "password": "short"},
        )
    assert res.status_code == 400
    assert "Password" in res.json()["detail"]


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/auth/login",
            json={"email": "nobody@example.com", "password": "WrongPass1"},
        )
    assert res.status_code == 401
