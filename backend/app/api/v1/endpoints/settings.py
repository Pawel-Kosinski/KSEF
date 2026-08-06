"""Endpointy ustawień tenanta (m.in. token KSeF)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Tenant, User
from app.database.session import get_db
from app.dependencies.tenant import (
    TenantContext,
    get_current_tenant,
    get_rls_session,
    require_admin_user,
)
from app.schemas.settings import (
    ContractorRuleCreate,
    ContractorRuleItem,
    ContractorRuleListResponse,
    KsefSettingsStatus,
    KsefTokenUpdate,
    TeamMemberItem,
    TeamResponse,
    TenantCategoryCreate,
    TenantCategoryItem,
    TenantCategoryListResponse,
    TenantCategoryUpdate,
)
from app.services.contractor_rule_management import (
    ContractorRuleDuplicateError,
    ContractorRuleInvalidCategoryError,
    ContractorRuleManagementService,
    ContractorRuleNotFoundError,
)
from app.services.encryption_service import EncryptionError, encrypt_ksef_token
from app.services.tenant_category_management import (
    CategoryDuplicateError,
    CategoryInUseError,
    CategoryNotFoundError,
    TenantCategoryManagementService,
)

router = APIRouter(prefix="/settings", tags=["Ustawienia"])


def _category_service(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> TenantCategoryManagementService:
    return TenantCategoryManagementService(session, tenant.tenant_id)


def _contractor_rule_service(
    tenant: TenantContext = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_rls_session),
) -> ContractorRuleManagementService:
    return ContractorRuleManagementService(session, tenant.tenant_id)


@router.get("/team", response_model=TeamResponse)
async def get_team(
    user: User = Depends(require_admin_user),
    session: AsyncSession = Depends(get_db),
) -> TeamResponse:
    tenant = await session.get(Tenant, user.tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Firma nie istnieje",
        )

    result = await session.execute(
        select(User)
        .where(User.tenant_id == user.tenant_id)
        .order_by(User.created_at.asc())
    )
    members = result.scalars().all()

    return TeamResponse(
        invite_token=tenant.invite_token,
        members=[
            TeamMemberItem(
                id=member.id,
                email=member.email,
                role=member.role,
                is_active=member.is_active,
                created_at=member.created_at,
            )
            for member in members
        ],
    )


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


@router.get("/categories", response_model=TenantCategoryListResponse)
async def list_tenant_categories(
    service: TenantCategoryManagementService = Depends(_category_service),
) -> TenantCategoryListResponse:
    items = await service.list_categories()
    return TenantCategoryListResponse(
        categories=[TenantCategoryItem(**item) for item in items]
    )


@router.post(
    "/categories",
    response_model=TenantCategoryItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_tenant_category(
    body: TenantCategoryCreate,
    service: TenantCategoryManagementService = Depends(_category_service),
    session: AsyncSession = Depends(get_rls_session),
) -> TenantCategoryItem:
    try:
        item = await service.create_category(body.name)
        await session.commit()
        return TenantCategoryItem(**item)
    except CategoryDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Kategoria „{exc.args[0]}” już istnieje",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.put("/categories/{category_id}", response_model=TenantCategoryItem)
async def update_tenant_category(
    category_id: UUID,
    body: TenantCategoryUpdate,
    service: TenantCategoryManagementService = Depends(_category_service),
    session: AsyncSession = Depends(get_rls_session),
) -> TenantCategoryItem:
    try:
        item = await service.update_category(category_id, body.name)
        await session.commit()
        return TenantCategoryItem(**item)
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kategoria nie istnieje",
        ) from exc
    except CategoryDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Kategoria „{exc.args[0]}” już istnieje",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant_category(
    category_id: UUID,
    service: TenantCategoryManagementService = Depends(_category_service),
    session: AsyncSession = Depends(get_rls_session),
) -> None:
    try:
        await service.delete_category(category_id)
        await session.commit()
    except CategoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Kategoria nie istnieje",
        ) from exc
    except CategoryInUseError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Nie można usunąć kategorii przypisanej do {exc.usage_count} "
                "pozycji faktur lub reguł kontrahentów"
            ),
        ) from exc


@router.get("/contractor-rules", response_model=ContractorRuleListResponse)
async def list_contractor_rules(
    service: ContractorRuleManagementService = Depends(_contractor_rule_service),
) -> ContractorRuleListResponse:
    items = await service.list_rules()
    return ContractorRuleListResponse(
        rules=[ContractorRuleItem(**item) for item in items]
    )


@router.post(
    "/contractor-rules",
    response_model=ContractorRuleItem,
    status_code=status.HTTP_201_CREATED,
)
async def create_contractor_rule(
    body: ContractorRuleCreate,
    service: ContractorRuleManagementService = Depends(_contractor_rule_service),
    session: AsyncSession = Depends(get_rls_session),
) -> ContractorRuleItem:
    try:
        item = await service.create_rule(
            body.contractor_nip,
            body.category_main,
            category_sub=body.category_sub,
            contractor_name=body.contractor_name,
        )
        await session.commit()
        return ContractorRuleItem(**item)
    except ContractorRuleDuplicateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Reguła dla NIP {exc.args[0]} już istnieje",
        ) from exc
    except ContractorRuleInvalidCategoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete("/contractor-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contractor_rule(
    rule_id: UUID,
    service: ContractorRuleManagementService = Depends(_contractor_rule_service),
    session: AsyncSession = Depends(get_rls_session),
) -> None:
    try:
        await service.delete_rule(rule_id)
        await session.commit()
    except ContractorRuleNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reguła nie istnieje",
        ) from exc
