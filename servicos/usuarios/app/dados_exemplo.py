"""Usuários de exemplo (só para aula). Todos usam a senha de SENHA_EXEMPLO.

A ordem é importante: os ids 1 a 5 são usados pelos dados de exemplo dos outros serviços.
"""
import os

from sqlalchemy.orm import Session

from app import servico as usuarios
from app.esquemas import UsuarioCriar

SENHA = os.getenv("SENHA_EXEMPLO", "Helpdesk2026")

USUARIOS = [
    ("Admin TI", "admin@empresa.com", "admin"),          # id 1
    ("Ana Souza", "ana@empresa.com", "solicitante"),     # id 2
    ("Bruno Lima", "bruno@empresa.com", "solicitante"),  # id 3
    ("Carla Dias", "carla@empresa.com", "tecnico"),      # id 4
    ("Diego Rocha", "diego@empresa.com", "tecnico"),     # id 5
]


def carregar(db: Session) -> None:
    if usuarios.listar(db):
        return
    for nome, email, perfil in USUARIOS:
        usuarios.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=SENHA))
