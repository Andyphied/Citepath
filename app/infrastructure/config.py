"""Application settings loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache
from typing import Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageBackend(StrEnum):
    LOCAL = "local"
    S3 = "s3"


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """AtlasOps configuration via environment variables (12-factor)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Required core
    DATABASE_URL: str = Field(
        ...,
        description="PostgreSQL connection string",
    )
    REDIS_URL: str = Field(
        ...,
        description="Redis broker URL",
    )
    JWT_SECRET_KEY: str = Field(
        ...,
        min_length=1,
        description="HS256 secret for JWT signing",
    )
    STORAGE_BACKEND: StorageBackend = Field(
        ...,
        description="Document storage backend: local or s3",
    )
    LLM_PROVIDER: LLMProvider = Field(
        ...,
        description="LLM provider: openai or anthropic",
    )

    # Optional with defaults
    JWT_EXPIRY_HOURS: int = Field(default=24, ge=1)
    EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    CHAT_MODEL: str = Field(default="gpt-4o-mini")
    RETRIEVAL_MIN_SCORE: float = Field(default=0.72, ge=0.0, le=1.0)
    MAX_UPLOAD_BYTES: int = Field(default=20_971_520, ge=1)
    CHUNK_SIZE_TOKENS: int = Field(
        default=1000,
        ge=100,
        le=5000,
        description="Target token count per document chunk",
    )
    CHUNK_OVERLAP_TOKENS: int = Field(
        default=150,
        ge=0,
        le=1000,
        description="Token overlap between consecutive chunks",
    )
    EMBEDDING_BATCH_SIZE: int = Field(
        default=64,
        ge=1,
        le=2048,
        description="Number of chunks per embedding API batch",
    )
    LOG_LEVEL: str = Field(default="INFO")
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)
    STORAGE_PATH: str = Field(
        default="/uploads",
        description="Local filesystem path when STORAGE_BACKEND=local",
    )

    # Conditional (validated below)
    S3_BUCKET: str | None = Field(default=None)
    AWS_REGION: str | None = Field(default=None)
    OPENAI_API_KEY: str | None = Field(default=None)
    ANTHROPIC_API_KEY: str | None = Field(default=None)

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def jwt_secret_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError(
                "JWT_SECRET_KEY is required and must not be empty "
                "(set a strong secret for JWT token signing)"
            )
        return value

    @model_validator(mode="after")
    def validate_conditional_settings(self) -> Self:
        if self.STORAGE_BACKEND == StorageBackend.S3:
            if not self.S3_BUCKET:
                raise ValueError(
                    "S3_BUCKET is required when STORAGE_BACKEND is s3"
                )
            if not self.AWS_REGION:
                raise ValueError(
                    "AWS_REGION is required when STORAGE_BACKEND is s3"
                )

        if self.LLM_PROVIDER == LLMProvider.OPENAI and not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required when LLM_PROVIDER is openai"
            )

        if (
            self.LLM_PROVIDER == LLMProvider.ANTHROPIC
            and not self.ANTHROPIC_API_KEY
        ):
            raise ValueError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER is anthropic"
            )

        if self.CHUNK_OVERLAP_TOKENS >= self.CHUNK_SIZE_TOKENS:
            raise ValueError(
                "CHUNK_OVERLAP_TOKENS must be less than CHUNK_SIZE_TOKENS"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance; validates on first access."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear cached settings (for tests)."""
    get_settings.cache_clear()
