from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, computed_field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True
    )

    PROJECT_NAME: str = "GraphQL Blog Platform"
    VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 資料庫配置（單獨項目）
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "blog_user"
    DB_PASSWORD: str = "blog_password"
    DB_NAME: str = "blog_db"
    TEST_DB_NAME: str = "test_blog"

    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 天

    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://192.168.85.157:5173",
        "http://172.21.0.1:5173",
        "http://172.20.0.1:5173",
        "http://172.22.0.1:5173",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        """動態組合資料庫 URL，確保與獨立配置項同步"""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


settings = Settings()