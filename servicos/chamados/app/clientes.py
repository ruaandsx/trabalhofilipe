"""Chamadas HTTP para os serviços de Usuários e de Inventário.

No monólito, isto era uma chamada de função (`usuarios.obter_tecnico(db, id)`). Agora é uma chamada
pela rede, que pode demorar, falhar ou nem chegar. Por isso:
- todo pedido tem `timeout`;
- erro de rede, timeout ou resposta 5xx viram ServicoIndisponivel (o cliente recebe 503);
- o token do usuário é repassado no cabeçalho Authorization.
"""
import logging

import httpx
from fastapi import HTTPException

from app import config
from app.auth import NAO_AUTENTICADO
from app.erros import NaoEncontrado, ServicoIndisponivel

log = logging.getLogger("chamados.clientes")

# Só os testes mexem nisto (para simular o outro serviço sem rede)
TRANSPORTE: httpx.BaseTransport | None = None


def _buscar(servico: str, base: str, caminho: str, token: str) -> dict | None:
    """GET no outro serviço. Devolve o JSON, ou None se ele respondeu 404."""
    tempo = httpx.Timeout(config.TIMEOUT_SEGUNDOS, connect=config.TIMEOUT_CONEXAO_SEGUNDOS)
    try:
        with httpx.Client(base_url=base, timeout=tempo, transport=TRANSPORTE) as http:
            resposta = http.get(caminho, headers={"Authorization": f"Bearer {token}"})
    except httpx.HTTPError as erro:  # recusou a conexão, não achou o nome, estourou o tempo...
        log.warning("Falha ao chamar %s%s: %s", base, caminho, type(erro).__name__)
        raise ServicoIndisponivel(servico) from erro

    if resposta.status_code == 200:
        return resposta.json()
    if resposta.status_code == 404:
        return None
    if resposta.status_code == 401:
        raise NAO_AUTENTICADO  # o outro serviço não aceitou o token (ex.: conta desativada)
    if resposta.status_code == 403:
        raise HTTPException(status_code=403, detail="Você não tem permissão para esta ação.")
    log.warning("%s respondeu %s em %s", servico, resposta.status_code, caminho)
    raise ServicoIndisponivel(servico)


def obter_usuario(usuario_id: int, token: str) -> dict:
    """GET /usuarios/{id} no serviço de Usuários."""
    dados = _buscar("Usuários", config.USUARIOS_URL, f"/usuarios/{usuario_id}", token)
    if dados is None:
        raise NaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    return dados


def obter_ativo(ativo_id: int, token: str) -> dict:
    """GET /ativos/{id} no serviço de Inventário."""
    dados = _buscar("Inventário", config.INVENTARIO_URL, f"/ativos/{ativo_id}", token)
    if dados is None:
        raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
    return dados
