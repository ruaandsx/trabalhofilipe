"""Configurações lidas das variáveis de ambiente."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./notificacoes.db")


def _ler_segredo() -> str:
    """O segredo vem do ambiente (JWT_SEGREDO) ou de um arquivo (JWT_SEGREDO_ARQUIVO). Nunca do código.

    Todos os serviços precisam usar o MESMO segredo, para conferir os tokens emitidos pelo serviço de Usuários.
    """
    segredo = os.getenv("JWT_SEGREDO", "")
    arquivo = os.getenv("JWT_SEGREDO_ARQUIVO")
    if not segredo and arquivo and Path(arquivo).exists():
        segredo = Path(arquivo).read_text().strip()
    if len(segredo) < 32:
        raise RuntimeError("Defina JWT_SEGREDO (ou JWT_SEGREDO_ARQUIVO) com pelo menos 32 caracteres.")
    return segredo


JWT_SEGREDO = _ler_segredo()
JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
STREAM_EVENTOS = "chamados.eventos"
GRUPO = "notificacoes"
CONSUMIDOR = os.getenv("HOSTNAME", "notificacoes-1")
