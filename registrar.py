import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

OM_BASE = os.getenv("OM_BASE")
BASIC_B64 = os.getenv("BASIC_B64")
TOKEN_KEY = os.getenv("TOKEN_KEY")

class NovoAluno(BaseModel):
    nome: str
    email: str | None = None
    cpf: str
    telefone: str | None = None
    celular: str | None = None
    senha: str

@router.post("/cadastro", summary="Registra novo aluno na plataforma")
def registrar(dados: NovoAluno):
    if not OM_BASE or not BASIC_B64 or not TOKEN_KEY:
        raise HTTPException(500, detail="Variáveis de ambiente OM não configuradas.")

    payload = {
        "token": TOKEN_KEY,
        "nome": dados.nome,
        "email": dados.email or "",
        "fone": dados.telefone or "",
        "celular": dados.celular or "",
        "doc_cpf": dados.cpf,
        "senha": dados.senha,
    }

    try:
        r = requests.post(f"{OM_BASE}/alunos", headers={"Authorization": f"Basic {BASIC_B64}"}, data=payload, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(500, detail=f"Erro de conexão: {e}")

    if r.ok:
        resp = r.json()
        if resp.get("status") == "true":
            return {"ok": True, "data": resp.get("data")}
        raise HTTPException(400, detail=resp.get("mensagem", "Falha no cadastro"))
    raise HTTPException(r.status_code, detail=r.text)
