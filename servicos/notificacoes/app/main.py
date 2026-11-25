"""Serviço de Notificações: consome os eventos dos chamados e guarda os avisos de cada usuário."""
import threading
from contextlib import asynccontextmanager

import redis
from fastapi import FastAPI

from app import config, consumidor
from app.database import Base, engine
from app.limite_corpo import LimiteDeCorpo
from app.rotas import router as notificacoes_router


def _nova_conexao() -> redis.Redis:
    return redis.Redis.from_url(config.REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=5)


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    Base.metadata.create_all(engine)
    parar = threading.Event()
    thread = None
    if config.REDIS_URL:
        conexao = _nova_conexao()  # uma conexão só para a thread
        thread = threading.Thread(target=consumidor.repetir, args=(lambda: conexao, parar), daemon=True)
        thread.start()
    yield
    parar.set()


app = FastAPI(title="Serviço de Notificações", version="3.0.0", lifespan=ciclo_de_vida,
              docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(LimiteDeCorpo)
app.include_router(notificacoes_router)


@app.get("/saude", tags=["Saúde"])
def saude():
    return {"status": "ok", "servico": "notificacoes"}
