"""Endpointy ustawień tenanta (m.in. token KSeF)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant
from app.database.session import get_db
from app.dependencies.tenant import TenantContext, get_current_tenant
from app.schemas.settings import KsefSettingsStatus, KsefTokenUpdate
from app.services.encryption_service import EncryptionError, encrypt_ksef_token

router = APIRouter(prefix="/settings", tags=["Ustawienia"])


@router.get("/ksef", response_model=KsefSettingsStatus)
async def get_ksef_settings(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> KsefSettingsStatus:
    row = await session.get(Tenant, tenant.tenant_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono tenanta",
        )
    return KsefSettingsStatus(is_configured=bool(row.encrypted_ksef_token))


@router.post("/ksef", response_model=KsefSettingsStatus)
async def save_ksef_token(
    body: KsefTokenUpdate,
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db),
) -> KsefSettingsStatus:
    row = await session.get(Tenant, tenant.tenant_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono tenanta",
        )

    try:
        row.encrypted_ksef_token = encrypt_ksef_token(body.ksef_token)
    except EncryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    await session.commit()
    return KsefSettingsStatus(is_configured=True)
