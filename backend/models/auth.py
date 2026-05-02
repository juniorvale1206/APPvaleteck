from typing import Optional
from pydantic import BaseModel, EmailStr


class LoginInput(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: str
    level: Optional[str] = None            # junior | n1 | n2 | n3 (None para admin)
    tutor_id: Optional[str] = None          # N3 supervisor (aplica-se a juniores)


class TokenOut(BaseModel):
    token: str          # legacy alias = access_token (compat com frontend antigo)
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int     # seconds for access token
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str


class RefreshOut(BaseModel):
    token: str          # legacy alias
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
