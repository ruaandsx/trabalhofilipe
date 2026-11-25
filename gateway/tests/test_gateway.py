import httpx
import pytest
from fastapi.testclient import TestClient

from app import main


class Falsos:
    """Simula os serviços. Guarda o último pedido recebido."""

    def __init__(self):
        self.fora = set()
        self.ultimo = None

    def __call__(self, req: httpx.Request) -> httpx.Response:
        self.ultimo = req
        servico = req.url.host
        if servico in self.fora:
            raise httpx.ConnectError("fora do ar")
        if servico == "lento":
            raise httpx.ReadTimeout("demorou")
        if req.url.path == "/saude":
            return httpx.Response(200, json={"status": "ok"})
        return httpx.Response(201 if req.method == "POST" else 200, json={"servico": servico, "caminho": req.url.path},
                              headers={"X-Segredo-Interno": "x", "Content-Security-Policy": "ruim"})


@pytest.fixture
def falsos(monkeypatch):
    f = Falsos()
    monkeypatch.setattr(main, "TRANSPORTE", httpx.MockTransport(f))
    return f


@pytest.fixture
def cliente(falsos):
    return TestClient(main.app)


def test_cada_rota_vai_para_o_servico_certo(cliente):
    esperado = {"/auth/login": "usuarios", "/usuarios/3": "usuarios", "/ativos": "inventario",
                "/chamados/painel": "chamados", "/notificacoes": "notificacoes"}
    for rota, servico in esperado.items():
        r = cliente.get(rota)
        assert r.json() == {"servico": servico, "caminho": rota}, rota


def test_metodo_corpo_query_e_token_seguem_adiante(cliente, falsos):
    r = cliente.post("/chamados?x=1", json={"a": 1}, headers={"Authorization": "Bearer abc", "Cookie": "segredo=1"})
    assert r.status_code == 201
    assert falsos.ultimo.method == "POST" and falsos.ultimo.url.query == b"x=1"
    assert falsos.ultimo.read() == b'{"a":1}' or b'"a"' in falsos.ultimo.read()
    assert falsos.ultimo.headers["authorization"] == "Bearer abc"
    assert "cookie" not in falsos.ultimo.headers


def test_rota_desconhecida_e_404(cliente):
    assert cliente.get("/qualquer-coisa").status_code == 404
    assert cliente.get("/docs").status_code == 404


def test_cabecalhos_de_seguranca_sao_do_gateway(cliente):
    r = cliente.get("/chamados")
    assert "x-segredo-interno" not in r.headers
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert r.headers["x-frame-options"] == "DENY"


def test_tela_e_servida_pelo_gateway(cliente):
    assert "html" in cliente.get("/").headers["content-type"]
    assert cliente.get("/app.js").status_code == 200 and cliente.get("/estilo.css").status_code == 200


def test_servico_fora_do_ar_da_503_claro(cliente, falsos):
    falsos.fora.add("inventario")
    r = cliente.get("/ativos")
    assert r.status_code == 503 and "indisponível" in r.json()["detail"]
    assert cliente.get("/chamados").status_code == 200  # os outros continuam


def test_timeout_da_504(cliente, monkeypatch):
    monkeypatch.setitem(main.config.ROTAS, "chamados", "http://lento:8000")
    assert cliente.get("/chamados").status_code == 504


def test_saude_agrega_os_servicos(cliente, falsos):
    r = cliente.get("/saude")
    assert r.status_code == 200 and r.json()["status"] == "ok" and len(r.json()["servicos"]) == 4
    falsos.fora.add("chamados")
    r = cliente.get("/saude")
    assert r.status_code == 503 and r.json()["servicos"]["chamados"] == "fora do ar"


def test_requisicao_grande_demais(cliente):
    r = cliente.post("/chamados", content="x" * 70000, headers={"Content-Type": "application/json"})
    assert r.status_code == 413


def test_tela_escapa_o_html():
    from pathlib import Path
    js = (Path(main.__file__).parent / "web" / "app.js").read_text()
    assert "const esc =" in js and "onclick" not in js
