"""Testes do serviço de Usuários: login, tokens, permissões e cadastro."""
from datetime import datetime, timedelta, timezone

import jwt

from app import config
from app.modelos import Usuario
from tests.conftest import SENHA


def token_falso(sub, segredo=config.JWT_SEGREDO, algoritmo="HS256", **extra):
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(sub), "iss": config.JWT_EMISSOR, "iat": agora, "exp": agora + timedelta(hours=1), **extra}
    return jwt.encode(dados, None if algoritmo == "none" else segredo, algorithm=algoritmo)


# ---------- login e token ----------

def test_rotas_exigem_login(cliente, contas):
    for metodo, rota in [("get", "/usuarios"), ("get", "/usuarios/1"), ("get", "/auth/eu"), ("post", "/usuarios")]:
        assert getattr(cliente, metodo)(rota).status_code == 401, rota


def test_login_devolve_token_com_perfil(cliente, contas):
    r = cliente.post("/auth/login", json={"email": "carla@x.com", "senha": SENHA}).json()
    dados = jwt.decode(r["access_token"], config.JWT_SEGREDO, algorithms=["HS256"], issuer=config.JWT_EMISSOR)
    assert dados["perfil"] == "tecnico" and dados["sub"] == str(r["usuario"]["id"])


def test_login_com_senha_errada_e_email_inexistente_tem_a_mesma_mensagem(cliente, contas):
    a = cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    b = cliente.post("/auth/login", json={"email": "ninguem@x.com", "senha": "errada123"})
    assert a.status_code == b.status_code == 401
    assert a.json()["detail"] == b.json()["detail"] == "E-mail ou senha inválidos."


def test_bloqueio_apos_varias_senhas_erradas(cliente, contas):
    for _ in range(config.LOGIN_MAX_FALHAS):
        cliente.post("/auth/login", json={"email": "ana@x.com", "senha": "errada123"})
    assert cliente.post("/auth/login", json={"email": "ana@x.com", "senha": SENHA}).status_code == 429


def test_token_adulterado(cliente, contas):
    token = contas["ana"]["headers"]["Authorization"] + "x"
    assert cliente.get("/auth/eu", headers={"Authorization": token}).status_code == 401


def test_token_assinado_com_outro_segredo(cliente, contas):
    falso = token_falso(contas["admin"]["id"], segredo="segredo-de-outra-pessoa-com-mais-de-32-caracteres")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_sem_assinatura_alg_none(cliente, contas):
    falso = token_falso(contas["admin"]["id"], algoritmo="none")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_token_expirado(cliente, contas):
    antigo = datetime.now(timezone.utc) - timedelta(hours=2)
    vencido = jwt.encode({"sub": str(contas["ana"]["id"]), "iss": config.JWT_EMISSOR, "iat": antigo,
                          "exp": antigo + timedelta(minutes=5)}, config.JWT_SEGREDO, algorithm="HS256")
    assert cliente.get("/auth/eu", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401


def test_senha_guardada_com_hash(sessao, contas):
    with sessao() as db:
        u = db.query(Usuario).filter_by(email="ana@x.com").one()
        assert SENHA not in u.senha_hash and u.senha_hash.startswith("scrypt$")


def test_senha_fraca_e_recusada(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "solicitante", "senha": "abcdefgh"})
    assert r.status_code == 422


# ---------- permissões e cadastro ----------

def test_solicitante_nao_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["ana"]["headers"],
                     json={"nome": "Eva", "email": "eva@x.com", "perfil": "admin", "senha": "Forte1234"})
    assert r.status_code == 403


def test_admin_cria_usuario(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Davi", "email": "davi@x.com", "perfil": "tecnico", "senha": "Forte1234"})
    assert r.status_code == 201
    assert "senha" not in r.json() and "senha_hash" not in r.json()


def test_email_repetido_e_recusado(cliente, contas):
    dados = {"nome": "Ana 2", "email": "ANA@x.com", "perfil": "solicitante", "senha": "Forte1234"}
    assert cliente.post("/usuarios", headers=contas["admin"]["headers"], json=dados).status_code == 422


def test_usuario_inexistente(cliente, contas):
    assert cliente.get("/usuarios/99", headers=contas["ana"]["headers"]).status_code == 404


def test_lista_publica_nao_mostra_email(cliente, contas):
    lista = cliente.get("/usuarios", headers=contas["ana"]["headers"]).json()
    assert lista and all("email" not in u for u in lista)


def test_campo_extra_e_recusado(cliente, contas):
    r = cliente.post("/usuarios", headers=contas["admin"]["headers"],
                     json={"nome": "Davi", "email": "d@x.com", "perfil": "tecnico", "senha": "Forte1234", "ativo": False})
    assert r.status_code == 422


def test_requisicao_grande_demais(cliente, contas):
    corpo = '{"nome": "' + "x" * 70000 + '"}'
    r = cliente.post("/usuarios", headers={**contas["admin"]["headers"], "Content-Type": "application/json"}, content=corpo)
    assert r.status_code == 413


def test_usuario_desativado_perde_o_acesso(sessao, cliente, contas):
    with sessao() as db:
        db.query(Usuario).filter_by(email="ana@x.com").one().ativo = False
        db.commit()
    assert cliente.get("/auth/eu", headers=contas["ana"]["headers"]).status_code == 401


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok", "servico": "usuarios"}
