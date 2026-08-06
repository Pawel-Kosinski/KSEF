"""Endpointy rejestracji, logowania i profilu użytkownika."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, User
from app.database.session import get_db
from app.dependencies.tenant import get_current_user
from app.schemas.auth import RegisterRequest, TokenResponse, UserResponse
from app.services.ai.category_generator import generate_categories_for_industry
from app.services.auth_service import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.services.tenant_category_management import seed_tenant_categories

router = APIRouter(prefix="/auth", tags=["Autoryzacja"])

USER_ROLE_ADMIN = "admin"
USER_ROLE_USER = "user"


async def _ensure_email_available(session: AsyncSession, email: str) -> None:
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Konto z tym adresem e-mail już istnieje",
        )


async def _register_new_company(
    session: AsyncSession,
    body: RegisterRequest,
) -> TokenResponse:
    nip_taken = await session.execute(select(Tenant).where(Tenant.nip == body.nip))
    if nip_taken.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Firma z tym NIP jest już zarejestrowana",
        )

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    industry = body.industry.strip()

    tenant = Tenant(
        id=tenant_id,
        name=body.company_name.strip(),
        nip=body.nip,
        industry=industry,
        invite_token=str(uuid.uuid4()),
    )
    user = User(
        id=user_id,
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        tenant_id=tenant_id,
        is_active=True,
        role=USER_ROLE_ADMIN,
    )
    session.add(tenant)
    session.add(user)

    category_names = await generate_categories_for_industry(industry)
    await seed_tenant_categories(session, tenant_id, category_names)

    await session.flush()

    token = create_access_token(user.id, tenant.id, user.email)
    return TokenResponse(access_token=token)


async def _register_with_invite(
    session: AsyncSession,
    body: RegisterRequest,
) -> TokenResponse:
    result = await session.execute(
        select(Tenant).where(Tenant.invite_token == body.invite_token)
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nieprawidłowy kod zaproszenia",
        )

    user_id = uuid.uuid4()
    user = User(
        id=user_id,
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        tenant_id=tenant.id,
        is_active=True,
        role=USER_ROLE_USER,
    )
    session.add(user)
    await session.flush()

    token = create_access_token(user.id, tenant.id, user.email)
    return TokenResponse(access_token=token)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    await _ensure_email_available(session, body.email.lower().strip())

    if body.is_invite_registration:
        return await _register_with_invite(session, body)
    return await _register_new_company(session, body)


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
        role=user.role,
        company_name=tenant.name if tenant else None,
        nip=tenant.nip if tenant else None,
        industry=tenant.industry if tenant else None,
    )
