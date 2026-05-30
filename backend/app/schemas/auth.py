from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None  # Required when mfa_enabled=True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    mfa_required: bool = False  # True when MFA is enrolled but code not yet provided


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MFASetupResponse(BaseModel):
    provisioning_uri: str  # otpauth:// URI for QR code generation


class MFAVerifyRequest(BaseModel):
    totp_code: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
