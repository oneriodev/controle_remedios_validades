"""Ponto de entrada da API de Controle de Validades."""

from fastapi import FastAPI

from app.routers import health, produtos, validades
from app.routers import auth, health, produtos, validades


app = FastAPI(
    title="API de Controle de Validades Farmacêuticas",
    description="MVP para controle FEFO de lotes e validades em farmácias.",
    version="0.1.0",
)

app.include_router(health.router)
app.include_router(produtos.router)
app.include_router(validades.router)