from datetime import datetime, timedelta

from app import config
from app.servico import HORAS_SLA


def abrir(cliente, h, **extra):
    return cliente.post("/chamados", headers=h, json={"titulo": "Teste", "descricao": "Teste", "prioridade": "baixa", **extra})


def eventos_na_fila(fila):
    return [campos for _, campos in fila.xrange(config.STREAM_EVENTOS)]


# ---------- regras (as mesmas do monólito) ----------

def test_sla_por_prioridade(cliente, contas):
    for prioridade, horas in HORAS_SLA.items():
        c = abrir(cliente, contas["ana"]["headers"], prioridade=prioridade).json()
        diferenca = datetime.fromisoformat(c["prazo_sla"]) - datetime.fromisoformat(c["criado_em"])
        assert diferenca == timedelta(hours=horas)


def test_solicitante_vem_do_token(cliente, contas):
    assert abrir(cliente, contas["ana"]["headers"]).json()["solicitante_id"] == contas["ana"]["id"]


def test_fluxo_completo(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    carla = contas["carla"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=carla["headers"], json={"tecnico_id": carla["id"]})
    assert r.json()["status"] == "em_atendimento" and r.json()["tecnico_id"] == carla["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=carla["headers"], json={"status": "resolvido"})
    assert r.json()["status"] == "resolvido"
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"], json={"status": "fechado"})
    assert r.json()["status"] == "fechado"
    r = cliente.post(f"/chamados/{cid}/comentarios", headers=carla["headers"], json={"texto": "oi"})
    assert r.status_code == 422  # fechado não recebe comentários


def test_transicao_invalida(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["carla"]["headers"], json={"status": "resolvido"})
    assert r.status_code == 422


def test_so_tecnico_pode_ser_atribuido(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": contas["bia"]["id"]})
    assert r.status_code == 422
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 99})
    assert r.status_code == 404


def test_solicitante_reabre_chamado_resolvido(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    c = contas["carla"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=c["headers"], json={"tecnico_id": c["id"]})
    cliente.patch(f"/chamados/{cid}/status", headers=c["headers"], json={"status": "resolvido"})
    r = cliente.patch(f"/chamados/{cid}/status", headers=contas["ana"]["headers"], json={"status": "em_atendimento"})
    assert r.json()["status"] == "em_atendimento"


def test_painel_e_atrasados(cliente, contas):
    abrir(cliente, contas["ana"]["headers"])
    abrir(cliente, contas["bia"]["headers"])
    assert cliente.get("/chamados/painel", headers=contas["carla"]["headers"]).json() == {
        "total": 2, "por_status": {"aberto": 2}, "atrasados": 0}
    assert cliente.get("/chamados/painel", headers=contas["ana"]["headers"]).json()["total"] == 1


def test_comentario_usa_o_autor_do_token(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    r = cliente.post(f"/chamados/{cid}/comentarios", headers=contas["ana"]["headers"], json={"texto": "oi"})
    assert r.status_code == 201 and r.json()["autor_id"] == contas["ana"]["id"]


# ---------- permissões e segurança ----------

def test_rotas_exigem_token(cliente):
    for metodo, rota in [("get", "/chamados"), ("post", "/chamados"), ("get", "/chamados/painel"), ("get", "/chamados/1")]:
        assert getattr(cliente, metodo)(rota).status_code == 401, rota


def test_solicitante_nao_ve_chamado_de_outra_pessoa(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    assert cliente.get(f"/chamados/{cid}", headers=contas["bia"]["headers"]).status_code == 404
    assert cliente.get("/chamados", headers=contas["bia"]["headers"]).json() == []


def test_solicitante_nao_atribui_nem_resolve(cliente, contas):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    h = contas["ana"]["headers"]
    assert cliente.patch(f"/chamados/{cid}/atribuir", headers=h, json={"tecnico_id": 4}).status_code == 403
    assert cliente.patch(f"/chamados/{cid}/status", headers=h, json={"status": "em_atendimento"}).status_code == 403


def test_nao_da_para_abrir_ou_comentar_em_nome_de_outro(cliente, contas):
    assert abrir(cliente, contas["ana"]["headers"], solicitante_id=3).status_code == 422
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    r = cliente.post(f"/chamados/{cid}/comentarios", headers=contas["ana"]["headers"], json={"texto": "oi", "autor_id": 4})
    assert r.status_code == 422


def test_limites_de_entrada(cliente, contas):
    assert abrir(cliente, contas["ana"]["headers"], titulo="x" * 500).status_code == 422
    corpo = '{"titulo": "' + "x" * 70000 + '"}'
    r = cliente.post("/chamados", headers={**contas["ana"]["headers"], "Content-Type": "application/json"}, content=corpo)
    assert r.status_code == 413


def test_texto_com_html_e_guardado_como_texto(cliente, contas):
    r = abrir(cliente, contas["ana"]["headers"], titulo="<script>alert(1)</script>")
    assert r.status_code == 201 and r.json()["titulo"] == "<script>alert(1)</script>"


# ---------- comunicação com os outros serviços ----------

def test_token_e_repassado_e_ativo_e_validado(cliente, contas, outros):
    assert abrir(cliente, contas["ana"]["headers"], ativo_id=1).status_code == 201
    assert "/ativos/1" in outros.chamadas
    assert abrir(cliente, contas["ana"]["headers"], ativo_id=99).status_code == 404


def test_inventario_fora_do_ar_da_erro_claro_503(cliente, contas, outros):
    outros.fora.add("inventario")
    r = abrir(cliente, contas["ana"]["headers"], ativo_id=1)
    assert r.status_code == 503 and "Inventário" in r.json()["detail"] and r.headers["retry-after"]
    # sem equipamento, o chamado não depende do Inventário e continua funcionando
    assert abrir(cliente, contas["ana"]["headers"]).status_code == 201
    assert cliente.get("/chamados", headers=contas["ana"]["headers"]).status_code == 200


def test_usuarios_fora_do_ar_da_erro_claro_503(cliente, contas, outros):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    outros.fora.add("usuarios")
    r = cliente.patch(f"/chamados/{cid}/atribuir", headers=contas["carla"]["headers"], json={"tecnico_id": 4})
    assert r.status_code == 503 and "Usuários" in r.json()["detail"]
    # nada foi alterado
    assert cliente.get(f"/chamados/{cid}", headers=contas["carla"]["headers"]).json()["status"] == "aberto"


def test_timeout_vira_503(cliente, contas, outros, monkeypatch):
    import httpx
    from app import clientes

    def lento(request):
        raise httpx.ReadTimeout("demorou")
    monkeypatch.setattr(clientes, "TRANSPORTE", httpx.MockTransport(lento))
    assert abrir(cliente, contas["ana"]["headers"], ativo_id=1).status_code == 503


def test_resposta_5xx_do_outro_servico_vira_503(cliente, contas, monkeypatch):
    import httpx
    from app import clientes
    monkeypatch.setattr(clientes, "TRANSPORTE", httpx.MockTransport(lambda r: httpx.Response(500)))
    assert abrir(cliente, contas["ana"]["headers"], ativo_id=1).status_code == 503


def test_cliente_http_tem_timeout(monkeypatch):
    import httpx
    from app import clientes
    visto = {}
    original = httpx.Client

    def espiao(*args, **kwargs):
        visto["timeout"] = kwargs["timeout"]
        return original(*args, **kwargs)
    monkeypatch.setattr(httpx, "Client", espiao)
    monkeypatch.setattr(clientes, "TRANSPORTE", httpx.MockTransport(lambda r: httpx.Response(200, json={"id": 1})))
    clientes.obter_ativo(1, "t")
    assert visto["timeout"].read == config.TIMEOUT_SEGUNDOS and visto["timeout"].connect == config.TIMEOUT_CONEXAO_SEGUNDOS


# ---------- eventos ----------

def test_eventos_publicados(cliente, contas, fila):
    cid = abrir(cliente, contas["ana"]["headers"]).json()["id"]
    c = contas["carla"]
    cliente.patch(f"/chamados/{cid}/atribuir", headers=c["headers"], json={"tecnico_id": c["id"]})
    cliente.patch(f"/chamados/{cid}/status", headers=c["headers"], json={"status": "resolvido"})
    ev = eventos_na_fila(fila)
    assert [e["tipo"] for e in ev] == ["ChamadoAberto", "ChamadoAtribuido", "ChamadoResolvido"]
    assert [e["destinatario_id"] for e in ev] == [str(contas["ana"]["id"]), str(c["id"]), str(contas["ana"]["id"])]


def test_fila_fora_do_ar_nao_derruba_o_chamado(cliente, contas, monkeypatch):
    import redis
    from app import eventos

    class Quebrada:
        def xadd(self, *a, **k):
            raise redis.ConnectionError("fora do ar")
    eventos.usar_conexao(Quebrada())
    assert abrir(cliente, contas["ana"]["headers"]).status_code == 201


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok", "servico": "chamados"}


def test_token_invalido_e_recusado_pelo_proprio_servico(cliente):
    """O serviço confere o token sozinho, mesmo sem passar pelo gateway."""
    from datetime import timedelta
    from tests.ajudas import fazer_token
    casos = {
        "adulterado": fazer_token(2, "solicitante") + "x",
        "outro segredo": fazer_token(2, "solicitante", segredo="segredo-de-outra-pessoa-com-mais-de-32-caracteres"),
        "alg none": fazer_token(2, "solicitante", algoritmo="none"),
        "expirado": fazer_token(2, "solicitante", validade=timedelta(hours=-1)),
        "emissor errado": fazer_token(2, "solicitante", emissor="outro"),
        "sem perfil": fazer_token(2, None),
        "perfil inventado": fazer_token(2, "superadmin"),
    }
    for nome, token in casos.items():
        assert cliente.get("/chamados", headers={"Authorization": f"Bearer {token}"}).status_code == 401, nome
