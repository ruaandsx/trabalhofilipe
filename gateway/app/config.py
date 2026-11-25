"""Configurações do gateway."""
import os

# Para onde cada grupo de rotas é encaminhado (nomes dos serviços no Docker Compose)
USUARIOS_URL = os.getenv("USUARIOS_URL", "http://usuarios:8000")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario:8000")
CHAMADOS_URL = os.getenv("CHAMADOS_URL", "http://chamados:8000")
NOTIFICACOES_URL = os.getenv("NOTIFICACOES_URL", "http://notificacoes:8000")

# O primeiro pedaço da rota decide o serviço: /chamados/7/status -> "chamados"
ROTAS = {
    "auth": USUARIOS_URL,
    "usuarios": USUARIOS_URL,
    "ativos": INVENTARIO_URL,
    "chamados": CHAMADOS_URL,
    "notificacoes": NOTIFICACOES_URL,
}
SERVICOS = {"usuarios": USUARIOS_URL, "inventario": INVENTARIO_URL, "chamados": CHAMADOS_URL,
            "notificacoes": NOTIFICACOES_URL}

# O chamado pode esperar outro serviço por até 3 s; o gateway espera um pouco mais que isso
TIMEOUT_SEGUNDOS = float(os.getenv("TIMEOUT_SEGUNDOS", "10"))
TIMEOUT_CONEXAO_SEGUNDOS = float(os.getenv("TIMEOUT_CONEXAO_SEGUNDOS", "2"))
TIMEOUT_SAUDE_SEGUNDOS = float(os.getenv("TIMEOUT_SAUDE_SEGUNDOS", "2"))

TAMANHO_MAXIMO_REQUISICAO = 64 * 1024
