import os

os.environ.setdefault("JWT_SEGREDO", "segredo-de-teste-com-mais-de-32-caracteres!!")
os.environ["DADOS_EXEMPLO"] = "0"

from datetime import datetime, timedelta, timezone

import jwt

from app import config


def fazer_token(usuario_id: int, perfil: str | None, segredo: str | None = None, algoritmo: str = "HS256",
                validade: timedelta = timedelta(hours=1), emissor: str = config.JWT_EMISSOR) -> str:
    """Cria um token como o serviço de Usuários criaria (só para os testes)."""
    agora = datetime.now(timezone.utc)
    dados = {"sub": str(usuario_id), "iss": emissor, "iat": agora, "exp": agora + validade}
    if perfil:
        dados["perfil"] = perfil
    chave = None if algoritmo == "none" else (segredo or config.JWT_SEGREDO)
    return jwt.encode(dados, chave, algorithm=algoritmo)


def cabecalho(usuario_id: int, perfil: str) -> dict:
    return {"Authorization": f"Bearer {fazer_token(usuario_id, perfil)}"}
