from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import servico
from app.auth import Usuario, usuario_atual
from app.database import get_db
from app.esquemas import NotificacaoSaida

router = APIRouter(prefix="/notificacoes", tags=["Notificações"])


@router.get("", response_model=list[NotificacaoSaida])
def minhas_notificacoes(usuario: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    """Cada usuário vê só as próprias notificações."""
    return servico.listar(db, usuario.id)
