from datetime import timedelta

from tests.ajudas import fazer_token

ATIVO = {"patrimonio": "PAT-1", "tipo": "computador", "descricao": "Desktop", "setor": "TI"}


def test_tecnico_cadastra_ativo_e_filtra_por_setor(cliente, contas):
    h = contas["carla"]
    cliente.post("/ativos", headers=h, json={**ATIVO, "tipo": "impressora", "descricao": "HP", "setor": "RH"})
    cliente.post("/ativos", headers=h, json={**ATIVO, "patrimonio": "PAT-2"})
    assert len(cliente.get("/ativos", params={"setor": "RH"}, headers=h).json()) == 1
    assert len(cliente.get("/ativos", headers=h).json()) == 2


def test_obter_ativo_e_inexistente(cliente, contas):
    criado = cliente.post("/ativos", headers=contas["carla"], json=ATIVO).json()
    assert cliente.get(f"/ativos/{criado['id']}", headers=contas["ana"]).json()["patrimonio"] == "PAT-1"
    assert cliente.get("/ativos/99", headers=contas["ana"]).status_code == 404


def test_patrimonio_repetido_e_recusado(cliente, contas):
    cliente.post("/ativos", headers=contas["carla"], json=ATIVO)
    assert cliente.post("/ativos", headers=contas["carla"], json=ATIVO).status_code == 422


def test_solicitante_nao_cadastra_ativo(cliente, contas):
    assert cliente.post("/ativos", headers=contas["ana"], json=ATIVO).status_code == 403


def test_campos_extras_e_limites(cliente, contas):
    assert cliente.post("/ativos", headers=contas["carla"], json={**ATIVO, "id": 5}).status_code == 422
    assert cliente.post("/ativos", headers=contas["carla"], json={**ATIVO, "descricao": "x" * 500}).status_code == 422


def test_requisicao_grande_demais(cliente, contas):
    r = cliente.post("/ativos", headers={**contas["carla"], "Content-Type": "application/json"},
                     content='{"descricao": "' + "x" * 70000 + '"}')
    assert r.status_code == 413


# ---------- token: o serviço confere sozinho, sem depender do gateway ----------

def test_rotas_exigem_token(cliente):
    for metodo, rota in [("get", "/ativos"), ("get", "/ativos/1"), ("post", "/ativos")]:
        assert getattr(cliente, metodo)(rota).status_code == 401, rota


def test_token_invalido_e_recusado(cliente):
    casos = {
        "adulterado": fazer_token(4, "tecnico") + "x",
        "outro segredo": fazer_token(4, "tecnico", segredo="segredo-de-outra-pessoa-com-mais-de-32-caracteres"),
        "alg none": fazer_token(4, "tecnico", algoritmo="none"),
        "expirado": fazer_token(4, "tecnico", validade=timedelta(hours=-1)),
        "emissor errado": fazer_token(4, "tecnico", emissor="outro"),
        "sem perfil": fazer_token(4, None),
        "perfil inventado": fazer_token(4, "superadmin"),
    }
    for nome, token in casos.items():
        r = cliente.get("/ativos", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401, nome


def test_saude_nao_exige_token(cliente):
    assert cliente.get("/saude").json() == {"status": "ok", "servico": "inventario"}
