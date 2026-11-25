"""Configurações do serviço de Usuários (lidas das variáveis de ambiente)."""
import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./usuarios.db")


def _ler_segredo() -> str:
    """O segredo vem do ambiente (JWT_SEGREDO) ou de um arquivo (JWT_SEGREDO_ARQUIVO). Nunca do código."""
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
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))

LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
