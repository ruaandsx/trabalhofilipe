from datetime import timedelta

from app import config, consumidor
from tests.ajudas import fazer_token


def publicar(fila, tipo, destinatario, mensagem="Olá"):
    fila.xadd(config.STREAM_EVENTOS, {"tipo": tipo, "destinatario_id": str(destinatario), "mensagem": mensagem,
                                      "ocorrido_em": "2026-01-01T00:00:00+00:00"})


def test_evento_vira_notificacao_do_destinatario(cliente, fila, contas):
    publicar(fila, "ChamadoAberto", 2, "Seu chamado #1 foi aberto.")
    publicar(fila, "ChamadoAtribuido", 4, "O chamado #1 foi atribuído a você.")
    assert consumidor.consumir_uma_vez(fila, bloqueio_ms=10) == 2
    ana = cliente.get("/notificacoes", headers=contas["ana"]).json()
    assert [n["tipo"] for n in ana] == ["ChamadoAberto"] and ana[0]["destinatario_id"] == 2
    assert [n["tipo"] for n in cliente.get("/notificacoes", headers=contas["carla"]).json()] == ["ChamadoAtribuido"]
    assert cliente.get("/notificacoes", headers=contas["bia"]).json() == []  # cada um vê só as suas


def test_evento_e_confirmado_e_nao_se_repete(cliente, fila, contas):
    publicar(fila, "ChamadoResolvido", 2)
    consumidor.consumir_uma_vez(fila, bloqueio_ms=10)
    assert consumidor.consumir_uma_vez(fila, bloqueio_ms=10) == 0
    assert consumidor.consumir_uma_vez(fila, ler="0") == 0  # nada pendente
    assert len(cliente.get("/notificacoes", headers=contas["ana"]).json()) == 1


def test_eventos_ruins_sao_descartados_sem_travar(cliente, fila, contas):
    fila.xadd(config.STREAM_EVENTOS, {"tipo": "ChamadoAberto"})                       # faltam campos
    publicar(fila, "TipoInventado", 2)                                                  # tipo desconhecido
    publicar(fila, "ChamadoAberto", 2, "valido")
    assert consumidor.consumir_uma_vez(fila, bloqueio_ms=10) == 3
    assert [n["mensagem"] for n in cliente.get("/notificacoes", headers=contas["ana"]).json()] == ["valido"]


def test_eventos_publicados_com_o_servico_fora_sao_lidos_depois(cliente, fila, contas):
    publicar(fila, "ChamadoAberto", 2)  # chega enquanto ninguém consome
    consumidor.garantir_grupo(fila)
    assert len(cliente.get("/notificacoes", headers=contas["ana"]).json()) == 0
    consumidor.consumir_uma_vez(fila, bloqueio_ms=10)
    assert len(cliente.get("/notificacoes", headers=contas["ana"]).json()) == 1


def test_rotas_exigem_token_valido(cliente):
    assert cliente.get("/notificacoes").status_code == 401
    for token in (fazer_token(2, "solicitante") + "x", fazer_token(2, "solicitante", algoritmo="none"),
                  fazer_token(2, "solicitante", validade=timedelta(hours=-1)), fazer_token(2, None)):
        assert cliente.get("/notificacoes", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_saude(cliente):
    assert cliente.get("/saude").json() == {"status": "ok", "servico": "notificacoes"}
