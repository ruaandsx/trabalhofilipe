"""Chamados de exemplo (só para aula).

Eles são gravados direto no banco deste serviço, sem chamar os outros. Os números de usuário e de
equipamento seguem a ordem dos dados de exemplo dos outros serviços:
usuários: 2 = Ana, 3 = Bruno, 4 = Carla (técnica); equipamentos: 1 = computador, 2 = impressora.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app import repositorio
from app.modelos import Chamado
from app.servico import calcular_prazo


def carregar(db: Session) -> None:
    if repositorio.listar(db):
        return
    agora = datetime.now()

    def novo(titulo, descricao, prioridade, solicitante_id, ativo_id=None, tecnico_id=None, status="aberto"):
        repositorio.salvar(db, Chamado(
            titulo=titulo, descricao=descricao, prioridade=prioridade, status=status, solicitante_id=solicitante_id,
            tecnico_id=tecnico_id, ativo_id=ativo_id, criado_em=agora, prazo_sla=calcular_prazo(prioridade, agora),
        ))

    novo("Computador não liga", "Apertei o botão e nada acontece.", "alta", 2, ativo_id=1, tecnico_id=4, status="em_atendimento")
    novo("Impressora atolando papel", "Atola a cada 3 folhas.", "media", 3, ativo_id=2)
    novo("Acesso ao sistema de RH", "Preciso de acesso para a nova estagiária.", "baixa", 3)
