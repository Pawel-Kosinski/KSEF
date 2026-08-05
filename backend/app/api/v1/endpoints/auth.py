"""Endpointy rejestracji, logowania i profilu użytkownika."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, TenantCategory, User
from app.database.session import get_db
from app.dependencies.tenant import get_current_user
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Autoryzacja"])

DEFAULT_TENANT_CATEGORIES = [
    "Materiały i Surowce",
    "Paliwa i Transport",
    "Koszty Biurowe i IT",
    "Usługi Zewnętrzne",
    "Opakowania",
    "Inne Koszty Operacyjne",
]


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    existing = await session.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konto z tym adresem e-mail już istnieje",
        )

    nip_taken = await session.execute(select(Tenant).where(Tenant.nip == body.nip))
    if nip_taken.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma z tym NIP jest już zarejestrowana",
        )

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    tenant = Tenant(
        id=tenant_id,
        name=body.company_name.strip(),
        nip=body.nip,
    )
    user = User(
        id=user_id,
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        tenant_id=tenant_id,
        is_active=True,
    )
    session.add(tenant)
    session.add(user)

    for index, category_name in enumerate(DEFAULT_TENANT_CATEGORIES, start=1):
        session.add(
            TenantCategory(
                tenant_id=tenant_id,
                name=category_name,
                sort_order=index,
            )
        )

    await session.flush()

    token = create_access_token(user.id, tenant.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    email = form_data.username.lower().strip()
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy e-mail lub hasło",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Konto jest nieaktywne",
        )

    token = create_access_token(user.id, user.tenant_id, user.email)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    tenant = await session.get(Tenant, user.tenant_id)
    return UserResponse(
        id=user.id,
        email=user.email,
        tenant_id=user.tenant_id,
        is_active=user.is_active,
        company_name=tenant.name if tenant else None,
        nip=tenant.nip if tenant else None,
    )
