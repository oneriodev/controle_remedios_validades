"""Classe base de todos os models (tabelas) do projeto."""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Padrão de nomes para restrições e índices.
# Sem isso, o PostgreSQL gera nomes aleatórios e as migrações futuras
# não conseguem encontrar a restrição para alterar ou remover.
CONVENCAO_NOMES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=CONVENCAO_NOMES)
