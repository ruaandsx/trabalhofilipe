"""Lê os eventos dos chamados na fila (Redis Streams) e registra as notificações.

Usa um "grupo de consumidores": o Redis lembra o que já foi entregue e o que ainda falta confirmar (ACK).
Se este serviço cair no meio do caminho, os eventos pendentes são lidos de novo ao voltar.
"""
import logging
import threading
import time

import redis
from sqlalchemy.orm import Session

from app import config, servico
from app.database import SessionLocal

log = logging.getLogger("notificacoes.consumidor")

TIPOS_ACEITOS = {"ChamadoAberto", "ChamadoAtribuido", "ChamadoResolvido"}


def garantir_grupo(conexao: redis.Redis) -> None:
    try:
        conexao.xgroup_create(config.STREAM_EVENTOS, config.GRUPO, id="0", mkstream=True)
    except redis.ResponseError as erro:
        if "BUSYGROUP" not in str(erro):  # o grupo já existe: tudo certo
            raise


def tratar(db: Session, campos: dict) -> None:
    """Transforma um evento em notificação. Evento mal formado é descartado (com aviso no log)."""
    try:
        tipo, destinatario, mensagem = campos["tipo"], int(campos["destinatario_id"]), campos["mensagem"]
    except (KeyError, ValueError):
        log.warning("Evento descartado (mal formado): %s", list(campos))
        return
    if tipo not in TIPOS_ACEITOS:
        log.warning("Evento descartado (tipo desconhecido): %s", tipo[:40])
        return
    servico.registrar(db, tipo, destinatario, mensagem)


def consumir_uma_vez(conexao: redis.Redis, bloqueio_ms: int = 1000, ler: str = ">") -> int:
    """Lê um lote de eventos (">" = novos; "0" = pendentes) e confirma cada um. Devolve quantos tratou."""
    garantir_grupo(conexao)
    resposta = conexao.xreadgroup(config.GRUPO, config.CONSUMIDOR, {config.STREAM_EVENTOS: ler},
                                  count=20, block=bloqueio_ms if ler == ">" else None)
    total = 0
    for _, mensagens in resposta or []:
        for id_evento, campos in mensagens:
            with SessionLocal() as db:
                tratar(db, campos)
            conexao.xack(config.STREAM_EVENTOS, config.GRUPO, id_evento)  # só confirma depois de salvar
            total += 1
    return total


def repetir(conexao_fabrica, parar: threading.Event) -> None:
    """Laço da thread: tenta de novo se o Redis estiver fora do ar."""
    pendentes_lidos = False
    while not parar.is_set():
        try:
            conexao = conexao_fabrica()
            if not pendentes_lidos:
                while consumir_uma_vez(conexao, ler="0"):
                    pass
                pendentes_lidos = True
            consumir_uma_vez(conexao)
        except (redis.RedisError, OSError) as erro:
            log.warning("Fila indisponível (%s). Nova tentativa em 2 s.", type(erro).__name__)
            parar.wait(2)
            pendentes_lidos = False
        except Exception:  # um erro inesperado não pode matar a thread
            log.exception("Erro ao tratar evento")
            parar.wait(2)
