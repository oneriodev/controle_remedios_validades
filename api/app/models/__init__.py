"""Ponto único de importação dos models.

Todo model novo deve ser importado aqui; é assim que o Alembic
"enxerga" as tabelas ao gerar migrações automaticamente.
"""

from app.models.base import Base
from app.models.farmacia import Farmacia
from app.models.lote_validade import LoteValidade
from app.models.produto import Produto
from app.models.usuario import Perfil, Usuario

__all__ = ["Base", "Farmacia", "LoteValidade", "Perfil", "Produto", "Usuario"]