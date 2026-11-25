"""Confere o token JWT emitido pelo serviço de Usuários.

Este serviço NÃO emite tokens: só confere a assinatura, o emissor e a validade. O id e o perfil
vêm do próprio token (assinado). Por isso uma conta desativada continua valendo até o token vencer.
"""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import JWT_ALGORITMO, JWT_EMISSOR, JWT_SEGREDO

PERFIS = {"solicitante", "tecnico", "admin"}
EQUIPE = ("tecnico", "admin")

esquema = HTTPBearer(auto_error=False)

NAO_AUTENTICADO = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Faça login para continuar.",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass(frozen=True)
class Usuario:
    """Quem está fazendo a requisição, segundo o token."""
    id: int
    perfil: str
    token: str  # guardado para repassar a outros serviços

    @property
    def eh_equipe(self) -> bool:
        return self.perfil in EQUIPE


def ler_token(token: str) -> Usuario:
    try:
        dados = jwt.decode(
            token, JWT_SEGREDO, algorithms=[JWT_ALGORITMO], issuer=JWT_EMISSOR,
            options={"require": ["exp", "iat", "sub", "iss"]},
        )
        perfil = dados["perfil"]
        if perfil not in PERFIS:
            raise ValueError("perfil inválido")
        return Usuario(id=int(dados["sub"]), perfil=perfil, token=token)
    except (jwt.PyJWTError, ValueError, KeyError) as erro:
        raise NAO_AUTENTICADO from erro


def usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> Usuario:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise NAO_AUTENTICADO
    return ler_token(credenciais.credentials)


def exigir_perfil(*perfis: str):
    """Libera a rota só para os perfis informados."""
    def verificar(usuario: Usuario = Depends(usuario_atual)) -> Usuario:
        if usuario.perfil not in perfis:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você não tem permissão para esta ação.")
        return usuario
    return verificar
