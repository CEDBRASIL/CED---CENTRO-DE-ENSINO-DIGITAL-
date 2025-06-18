import os
from datetime import datetime, timedelta
from typing import List

import requests
from fastapi import APIRouter, HTTPException

from cursos import CURSOS_OM
from matricular import (
    _obter_token_unidade,
    _cadastrar_aluno_om,
    _send_whatsapp_chatpro,
)
from asaas import _criar_ou_obter_cliente, ASAAS_BASE_URL, _headers
from utils import parse_valor

router = APIRouter(prefix="/teste-gratis", tags=["Teste Gratuito"])

TRIAL_DIAS = 3
SENHA_PADRAO = os.getenv("SENHA_PADRAO", "1234567")
VALOR_PADRAO = parse_valor(os.getenv("ASSINATURA_VALOR_PADRAO", "0")) or 0.0
BILLING_TYPE = os.getenv("ASAAS_BILLING_TYPE", "UNDEFINED")


def _calc_vencimento() -> str:
    return (datetime.now() + timedelta(days=TRIAL_DIAS)).strftime("%Y-%m-%d")


@router.post("")
def iniciar_teste(dados: dict):
    nome = dados.get("nome")
    whatsapp = dados.get("whatsapp")
    cpf = dados.get("cpf")
    curso = dados.get("curso") or (dados.get("cursos") or [None])[0]

    if not nome or not whatsapp or not curso:
        raise HTTPException(400, "Campos obrigatórios ausentes")

    cursos_ids: List[int] | None = CURSOS_OM.get(curso)
    if not cursos_ids:
        raise HTTPException(404, "Curso não encontrado")

    try:
        token = _obter_token_unidade()
        aluno_id, cpf_res = _cadastrar_aluno_om(
            nome,
            whatsapp,
            None,
            cursos_ids,
            token,
            SENHA_PADRAO,
            cpf=cpf,
        )

        customer_id = _criar_ou_obter_cliente(nome, cpf_res, whatsapp)
        venc_iso = _calc_vencimento()
        payload = {
            "customer": customer_id,
            "billingType": BILLING_TYPE,
            "value": VALOR_PADRAO,
            "cycle": "MONTHLY",
            "nextDueDate": venc_iso,
            "description": curso,
            "externalReference": ",".join(map(str, cursos_ids)),
        }
        resp = requests.post(
            f"{ASAAS_BASE_URL}/subscriptions",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        if not resp.ok:
            raise HTTPException(resp.status_code, resp.text)

        vence_fmt = datetime.fromisoformat(venc_iso).strftime("%d/%m/%Y")
        _send_whatsapp_chatpro(nome, whatsapp, [curso], cpf_res, vencimento=vence_fmt)

        data = resp.json()
        url = (
            data.get("chargeUrl")
            or data.get("invoiceUrl")
            or data.get("bankSlipUrl")
            or data.get("transactionReceiptUrl")
        )

        return {
            "status": "ok",
            "aluno_id": aluno_id,
            "cpf": cpf_res,
            "subscription": data.get("id"),
            "fatura_url": url,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
