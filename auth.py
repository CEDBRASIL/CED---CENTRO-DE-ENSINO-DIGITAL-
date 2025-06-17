from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import credenciais

router = APIRouter(prefix="/auth", tags=["Autenticacao"])

class LoginPayload(BaseModel):
    usuario: str
    senha: str

@router.post("/login")
def login(payload: LoginPayload):
    if payload.usuario == credenciais.LOGIN and payload.senha == credenciais.SENHA:
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Credenciais invalidas")
