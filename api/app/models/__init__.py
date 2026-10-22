"""Ponto único de importação dos models.

Todo model novo deve ser importado aqui; é assim que o Alembic
"enxerga" as tabelas ao gerar migrações automaticamente.
"""

from app.models.base import Base

__all__ = ["Base"]