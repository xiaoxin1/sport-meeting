from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str  # 管理员用户名 或 领队姓名
    password: str
    grade: str | None = None  # 领队登录必填；管理员留空
    class_name: str | None = None  # 领队登录必填；管理员留空


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str = "admin"  # "admin" | "leader"
    class_team_id: int | None = None
    grade: str | None = None
    class_name: str | None = None
