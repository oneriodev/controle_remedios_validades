"""Configuração central da API, lida do arquivo .env na raiz do projeto."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

# config.py está em api/app/core/ → subindo 3 níveis chegamos à raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=RAIZ_PROJETO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignora variáveis do .env que a API não usa
    )

    # Banco de dados
    postgres_user: str
    postgres_password: SecretStr
    postgres_db: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Segurança (usado na Etapa 5)
    jwt_secret_key: SecretStr
    jwt_access_token_minutes: int = 15
    jwt_refresh_token_days: int = 7

    # Fuso usado para calcular "hoje" nas faixas de vencimento
    fuso_horario: str = "America/Cuiaba"

    @field_validator("jwt_secret_key")
    @classmethod
    def exigir_chave_forte(cls, valor: SecretStr) -> SecretStr:
        # Chave curta = tokens forjáveis por força bruta. Melhor nem iniciar.
        if len(valor.get_secret_value()) < 32:
            raise ValueError(
                "JWT_SECRET_KEY muito curta. Gere uma com: "
                'python3 -c "import secrets; print(secrets.token_urlsafe(64))"'
            )
        return valor

    @property
    def database_url(self) -> URL:
        """URL de conexão assíncrona (driver psycopg 3)."""
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    """Lê o .env uma única vez e reaproveita o resultado."""
    return Settings()
