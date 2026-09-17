"""全局配置。所有可变项统一从环境变量读取，便于容器化部署。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # MySQL
    mysql_host: str = "mysql"
    mysql_port: int = 3306
    mysql_user: str = "sfls"
    mysql_password: str = "sfls_pwd_change_me"
    mysql_database: str = "sfls_meeting"

    # JWT / Auth
    jwt_secret: str = "change_me"
    jwt_expire_minutes: int = 720
    jwt_algorithm: str = "HS256"

    admin_username: str = "admin"
    admin_password: str = "admin123"

    # 领队账号 / 报名
    leader_default_password: str = "admin_sfls"  # 新建班级时领队默认登录密码
    reg_hint: str = "每个项目限报2人，每位运动员限报1项，可兼报接力"  # 报名详情红字提示
    reg_max_per_event: int = 2  # 每班每个项目限报人数
    reg_max_events_per_person: int = 1  # 每人限报(非接力)个人项目数

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"
    # 输出上限。0 或负数表示不传 max_tokens，由模型使用自身上限（V4 最高 384K）。
    deepseek_max_tokens: int = 0

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
