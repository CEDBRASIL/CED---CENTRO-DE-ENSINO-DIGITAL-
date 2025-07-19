# Integração simplificada com o ASAAS para checkout transparente
import os
import requests
from fastapi import APIRouter, HTTPException, Request
from matricular import realizar_matricula

ASAAS_TOKEN = os.getenv("ASAAS_TOKEN")
ASAAS_BASE = "https://api.asaas.com/v3"

router = APIRouter(prefix="/asaas", tags=["ASAAS"])


def _headers():
    if not ASAAS_TOKEN:
        raise RuntimeError("ASAAS_TOKEN não configurado")
    return {"Content-Type": "application/json", "access_token": ASAAS_TOKEN}


@router.post("/checkout")
async def criar_assinatura(dados: dict):
    """Cria assinatura para o aluno via ASAAS."""
    nome = dados.get("nome")
    whatsapp = dados.get("whatsapp")
    email = dados.get("email") or f"{whatsapp}@nao-informado.com"
    valor = dados.get("valor")
    curso = dados.get("curso")
    token_cartao = dados.get("creditCardToken")
    holder = dados.get("creditCardHolderInfo")

    if not all([nome, whatsapp, valor, curso, token_cartao, holder]):
        raise HTTPException(400, "Dados incompletos para o checkout")

    try:
        # cria cliente
        r = requests.post(
            f"{ASAAS_BASE}/customers",
            headers=_headers(),
            json={"name": nome, "mobilePhone": whatsapp, "email": email},
            timeout=10,
        )
        if not r.ok:
            raise HTTPException(r.status_code, r.text)
        customer_id = r.json().get("id")

        # cria assinatura
        payload = {
            "customer": customer_id,
            "billingType": "CREDIT_CARD",
            "value": valor,
            "cycle": "MONTHLY",
            "description": curso,
            "creditCardToken": token_cartao,
            "creditCardHolderInfo": holder,
            "remoteIp": dados.get("remoteIp"),
            "dueDate": dados.get("dueDate"),
            "notifyWhatsApp": False,
        }
        r2 = requests.post(
            f"{ASAAS_BASE}/subscriptions",
            headers=_headers(),
            json=payload,
            timeout=10,
        )
        if not r2.ok:
            raise HTTPException(r2.status_code, r2.text)
        return r2.json()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/webhook")
async def webhook(req: Request):
    """Processa eventos do ASAAS e matricula o aluno quando pago."""
    payload = await req.json()
    event = payload.get("event")
    payment = payload.get("payment")
    if event != "PAYMENT_RECEIVED" or not payment:
        return {"message": "Evento ignorado"}

    if payment.get("status") not in {"RECEIVED", "CONFIRMED"}:
        return {"message": "Pagamento não confirmado"}

    customer = payload.get("customer", {})
    nome = customer.get("name")
    whatsapp = customer.get("mobilePhone")
    email = customer.get("email")
    curso = payment.get("description")

    dados = {
        "nome": nome,
        "whatsapp": whatsapp,
        "email": email,
        "cursos": [curso] if curso else [],
    }
    try:
        await realizar_matricula(dados)
    except Exception:
        pass
    return {"status": "ok"}
