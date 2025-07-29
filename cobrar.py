import os
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/cobrar", tags=["Cobrança"])

# Variáveis lidas em cada requisição para evitar inconsistências
ASAAS_KEY = os.getenv("ASAAS_KEY")
ASAAS_BASE_URL = os.getenv("ASAAS_BASE_URL", "https://api.asaas.com/v3")


class ChargeData(BaseModel):
    customer: str
    value: float
    dueDate: str
    billingType: str = "BOLETO"
    description: str = "Cobrança"


@router.post("/")
def criar_cobranca(data: ChargeData):
    key = os.getenv("ASAAS_KEY")
    if not key:
        raise HTTPException(500, "ASAAS_KEY não configurada")

    url = f"{ASAAS_BASE_URL}/payments"
    headers = {"Content-Type": "application/json", "access_token": key}
    payload = data.dict()

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
    except requests.RequestException as e:
        raise HTTPException(502, f"Erro de conexão: {e}")

    if resp.ok:
        try:
            return resp.json()
        except Exception:
            return {"status": "ok"}

    raise HTTPException(resp.status_code, resp.text)
