"""Publicação de eventos na fila (Redis Streams). Quem consome é o serviço de Notificações.

Publicar é "dispare e esqueça": se a fila estiver fora do ar, o chamado continua sendo salvo
e o erro só vai para o log (o aviso se perde, mas o sistema não para).
"""
import logging
from datetime import datetime, timezone

import redis

from app import config

log = logging.getLogger("chamados.eventos")

_redis: redis.Redis | None = None


def _conexao() -> redis.Redis | None:
    global _redis
    if _redis is None and config.REDIS_URL:
        _redis = redis.Redis.from_url(
            config.REDIS_URL, decode_responses=True, socket_connect_timeout=1, socket_timeout=1,
        )
    return _redis


def usar_conexao(conexao: redis.Redis | None) -> None:
    """Troca a conexão (usado nos testes)."""
    global _redis
    _redis = conexao


def publicar(tipo: str, destinatario_id: int, mensagem: str) -> None:
    """Publica ChamadoAberto, ChamadoAtribuido ou ChamadoResolvido."""
    evento = {
        "tipo": tipo,
        "destinatario_id": str(destinatario_id),
        "mensagem": mensagem,
        "ocorrido_em": datetime.now(timezone.utc).isoformat(),
    }
    try:
        conexao = _conexao()
        if conexao is not None:
            conexao.xadd(config.STREAM_EVENTOS, evento, maxlen=10_000, approximate=True)
    except (redis.RedisError, OSError) as erro:
        log.warning("Não foi possível publicar o evento %s: %s", tipo, type(erro).__name__)
