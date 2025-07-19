import os
import re
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

OM_BASE = os.getenv("OM_BASE")
BASIC_B64 = os.getenv("BASIC_B64")
TOKEN_KEY = os.getenv("TOKEN_KEY")
UNIDADE_ID = os.getenv("UNIDADE_ID")

class NovoAluno(BaseModel):
    nome: str
    email: str | None = None
    cpf: str
    telefone: str | None = None
    celular: str | None = None
    senha: str

@router.post("/cadastro", summary="Registra novo aluno na plataforma")
def registrar(dados: NovoAluno):
    if not all([OM_BASE, BASIC_B64, TOKEN_KEY, UNIDADE_ID]):
        raise HTTPException(500, detail="Variáveis de ambiente OM não configuradas.")

    telefone = re.sub(r"\D", "", dados.celular or dados.telefone or "")
    cpf = re.sub(r"\D", "", dados.cpf)
    payload = {
        "token": TOKEN_KEY,
        "nome": dados.nome,
        "email": dados.email or f"{telefone}@nao-informado.com",
        "whatsapp": telefone,
        "fone": telefone,
        "celular": telefone,
        "data_nascimento": "2000-01-01",
        "doc_cpf": cpf,
        "doc_rg": "000000000",
        "pais": "Brasil",
        "uf": "DF",
        "cidade": "Brasília",
        "endereco": "Não informado",
        "bairro": "Centro",
        "cep": "70000-000",
        "complemento": "",
        "numero": "0",
        "unidade_id": UNIDADE_ID,
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
