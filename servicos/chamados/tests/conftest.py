import tests.ajudas  # noqa: F401  (define as variáveis de ambiente antes de importar o app)

import fakeredis
import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import clientes, config, eventos
from app.database import Base, get_db
from app.main import app
from tests.ajudas import cabecalho

USUARIOS = {1: "admin", 2: "solicitante", 3: "solicitante", 4: "tecnico"}
ATIVOS = {1: {"id": 1, "patrimonio": "PAT-1", "tipo": "computador", "descricao": "Desktop", "setor": "TI"}}


class OutrosServicos:
    """Simula os serviços de Usuários e de Inventário (sem rede). `fora` = lista de serviços caídos."""

    def __init__(self):
        self.fora: set[str] = set()
        self.chamadas: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.chamadas.append(request.url.path)
        partes = request.url.path.strip("/").split("/")
        servico = "usuarios" if partes[0] == "usuarios" else "inventario"
        if servico in self.fora:
            raise httpx.ConnectError("recusou a conexão")
        assert request.headers["authorization"].startswith("Bearer "), "o token deve ser repassado"
        numero = int(partes[1])
        if servico == "usuarios" and numero in USUARIOS:
            return httpx.Response(200, json={"id": numero, "nome": "X", "perfil": USUARIOS[numero]})
        if servico == "inventario" and numero in ATIVOS:
            return httpx.Response(200, json=ATIVOS[numero])
        return httpx.Response(404, json={"detail": "não encontrado"})


@pytest.fixture
def outros():
    simulado = OutrosServicos()
    clientes.TRANSPORTE = httpx.MockTransport(simulado)
    yield simulado
    clientes.TRANSPORTE = None


@pytest.fixture
def fila():
    conexao = fakeredis.FakeRedis(decode_responses=True)
    eventos.usar_conexao(conexao)
    yield conexao
    eventos.usar_conexao(None)


@pytest.fixture
def cliente(outros, fila):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def db_de_teste():
        db = Sessao()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = db_de_teste
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def contas():
    """ids iguais aos do simulador: 1 admin, 2 Ana, 3 Bia (solicitantes), 4 Carla (técnica)."""
    return {n: {"headers": cabecalho(i, p), "id": i} for n, i, p in
            [("admin", 1, "admin"), ("ana", 2, "solicitante"), ("bia", 3, "solicitante"), ("carla", 4, "tecnico")]}
