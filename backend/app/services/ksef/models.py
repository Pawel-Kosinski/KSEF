"""Modele Pydantic dla odpowiedzi KSeF API 2.0."""

from pydantic import BaseModel, Field


class AuthChallengeResponse(BaseModel):
    challenge: str
    timestamp: str
    timestamp_ms: int = Field(alias="timestampMs")
    client_ip: str = Field(alias="clientIp")

    model_config = {"populate_by_name": True}


class ContextIdentifier(BaseModel):
    type: str = "Nip"
    value: str


class KsefTokenAuthRequest(BaseModel):
    challenge: str
    context_identifier: ContextIdentifier = Field(alias="contextIdentifier")
    encrypted_token: str = Field(alias="encryptedToken")
    public_key_id: str | None = Field(default=None, alias="publicKeyId")

    model_config = {"populate_by_name": True, "by_alias": True}


class OperationToken(BaseModel):
    token: str
    valid_until: str = Field(alias="validUntil")

    model_config = {"populate_by_name": True}


class AuthInitResponse(BaseModel):
    reference_number: str = Field(alias="referenceNumber")
    authentication_token: OperationToken = Field(alias="authenticationToken")

    model_config = {"populate_by_name": True}


class AuthStatusInfo(BaseModel):
    code: int
    description: str


class AuthStatusResponse(BaseModel):
    status: AuthStatusInfo
    start_date: str | None = Field(default=None, alias="startDate")
    authentication_method: str | None = Field(default=None, alias="authenticationMethod")

    model_config = {"populate_by_name": True}


class AccessTokenPair(BaseModel):
    token: str
    valid_until: str = Field(alias="validUntil")

    model_config = {"populate_by_name": True}


class TokenRedeemResponse(BaseModel):
    access_token: AccessTokenPair = Field(alias="accessToken")
    refresh_token: AccessTokenPair = Field(alias="refreshToken")

    model_config = {"populate_by_name": True}


class PublicKeyCertificate(BaseModel):
    certificate: str
    certificate_id: str = Field(alias="certificateId")
    public_key_id: str = Field(alias="publicKeyId")
    valid_from: str = Field(alias="validFrom")
    valid_to: str | None = Field(default=None, alias="validTo")
    usage: list[str]

    model_config = {"populate_by_name": True}


class KsefAccessTokens(BaseModel):
    """Wynik pełnego procesu uwierzytelniania tokenem KSeF."""

    access_token: str
    refresh_token: str
    access_token_valid_until: str
    refresh_token_valid_until: str
    reference_number: str


# --- Eksport paczek faktur (POST /invoices/exports) ---


class ExportEncryptionInfo(BaseModel):
    encrypted_symmetric_key: str = Field(alias="encryptedSymmetricKey")
    initialization_vector: str = Field(alias="initializationVector")
    public_key_id: str | None = Field(default=None, alias="publicKeyId")

    model_config = {"populate_by_name": True, "by_alias": True}


class ExportDateRange(BaseModel):
    date_type: str = Field(alias="dateType")
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True, "by_alias": True}


class ExportFilters(BaseModel):
    subject_type: str = Field(alias="subjectType")
    date_range: ExportDateRange = Field(alias="dateRange")

    model_config = {"populate_by_name": True, "by_alias": True}


class InvoiceExportRequest(BaseModel):
    encryption: ExportEncryptionInfo
    filters: ExportFilters
    only_metadata: bool = Field(default=False, alias="onlyMetadata")

    model_config = {"populate_by_name": True, "by_alias": True}


class ExportInitResponse(BaseModel):
    reference_number: str = Field(alias="referenceNumber")

    model_config = {"populate_by_name": True}


class OperationStatusInfo(BaseModel):
    code: int
    description: str
    details: list[str] | None = None


class InvoicePackagePart(BaseModel):
    ordinal_number: int = Field(alias="ordinalNumber")
    part_name: str = Field(alias="partName")
    method: str
    url: str
    part_size: int = Field(alias="partSize")
    part_hash: str = Field(alias="partHash")
    encrypted_part_size: int = Field(alias="encryptedPartSize")
    encrypted_part_hash: str = Field(alias="encryptedPartHash")
    expiration_date: str = Field(alias="expirationDate")

    model_config = {"populate_by_name": True}


class InvoicePackage(BaseModel):
    invoice_count: int = Field(alias="invoiceCount")
    size: int
    parts: list[InvoicePackagePart]
    is_truncated: bool = Field(alias="isTruncated")

    model_config = {"populate_by_name": True}


class ExportStatusResponse(BaseModel):
    status: OperationStatusInfo
    completed_date: str | None = Field(default=None, alias="completedDate")
    package: InvoicePackage | None = None

    model_config = {"populate_by_name": True}


class InvoiceMetadataDateRange(BaseModel):
    date_type: str = Field(alias="dateType")
    from_: str = Field(alias="from")
    to: str | None = None

    model_config = {"populate_by_name": True, "by_alias": True}


class InvoiceMetadataQueryRequest(BaseModel):
    subject_type: str = Field(alias="subjectType")
    date_range: InvoiceMetadataDateRange = Field(alias="dateRange")

    model_config = {"populate_by_name": True, "by_alias": True}


class InvoiceMetadataItem(BaseModel):
    ksef_number: str = Field(alias="ksefNumber")

    model_config = {"populate_by_name": True}


class InvoiceMetadataQueryResponse(BaseModel):
    has_more: bool = Field(alias="hasMore")
    is_truncated: bool = Field(default=False, alias="isTruncated")
    invoices: list[InvoiceMetadataItem] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
