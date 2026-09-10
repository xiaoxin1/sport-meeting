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

    # DeepSeek
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"

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
