"""Skrypt pomocniczy do generowania tokenów JWT deweloperskich."""

import argparse
import asyncio
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jose import jwt
from sqlalchemy import select

from app.config import get_settings
from app.database.models import Tenant
from app.database.session import async_session_factory


def create_dev_token(tenant_id: str) -> str:
    settings = get_settings()
    payload = {
        "sub": "dev-user",
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


async def resolve_tenant_id(tenant_id: str | None, nip: str | None) -> str:
    if tenant_id:
        return tenant_id
    if nip:
        async with async_session_factory() as session:
            result = await session.execute(select(Tenant).where(Tenant.nip == nip))
            tenant = result.scalar_one_or_none()
            if tenant is None:
                raise SystemExit(f"Brak tenanta z NIP {nip!r}. Uruchom najpierw test_etl_pipeline.py.")
            return str(tenant.id)
    return str(uuid.uuid4())


async def main() -> int:
    parser = argparse.ArgumentParser(description="Generuj token JWT dla trybu deweloperskiego.")
    parser.add_argument("tenant_id", nargs="?", help="UUID tenanta z bazy")
    parser.add_argument(
        "--nip",
        help="NIP tenanta (np. 9998887776 z test_etl_pipeline.py)",
    )
    args = parser.parse_args()

    tenant_id = await resolve_tenant_id(args.tenant_id, args.nip)
    token = create_dev_token(tenant_id)
    print(f"tenant_id: {tenant_id}")
    print(f"token: {token}")
    print()
    print("Wklej do frontend/.env.local:")
    print(f"NEXT_PUBLIC_DEV_TOKEN={token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))