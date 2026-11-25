"""Erros de negócio e de comunicação com outros serviços."""


class NaoEncontrado(Exception):
    """O recurso pedido não existe (ou o usuário não pode vê-lo)."""


class RegraDeNegocio(Exception):
    """A operação viola uma regra do sistema."""


class SemPermissao(Exception):
    """O usuário está logado, mas não pode fazer esta operação."""


class ServicoIndisponivel(Exception):
    """Outro serviço está fora do ar, lento demais ou respondeu com erro."""

    def __init__(self, servico: str):
        self.servico = servico
        super().__init__(f"O serviço de {servico} está indisponível no momento. Tente novamente em instantes.")
