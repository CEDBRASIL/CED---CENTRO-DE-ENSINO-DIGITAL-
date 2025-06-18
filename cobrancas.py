import os
import requests
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/cobrancas", tags=["Cobranças"])

ASAAS_KEY = os.getenv("ASAAS_KEY")
ASAAS_BASE_URL = os.getenv("ASAAS_BASE_URL", "https://api.asaas.com/v3")


def _headers() -> dict:
    if not ASAAS_KEY:
        raise HTTPException(500, "ASAAS_KEY não configurada")
    return {"Content-Type": "application/json", "access_token": ASAAS_KEY}


_customer_cache: dict[str, tuple[str | None, str | None]] = {}


def _get_customer(cid: str) -> tuple[str | None, str | None]:
    if cid in _customer_cache:
        return _customer_cache[cid]
    try:
        resp = requests.get(
            f"{ASAAS_BASE_URL}/customers/{cid}", headers=_headers(), timeout=10
        )
        if resp.ok:
            data = resp.json()
            nome = data.get("name")
            tel = data.get("mobilePhone") or data.get("phone")
            _customer_cache[cid] = (nome, tel)
            return nome, tel
    except requests.RequestException:
        pass
    return None, None


@router.get("")
@router.get("/")
def listar_cobrancas(status: str | None = None):
    params = {"limit": 100}
    if status:
        params["status"] = status
    offset = 0
    cobrancas: list[dict] = []
    while True:
        params["offset"] = offset
        try:
            resp = requests.get(
                f"{ASAAS_BASE_URL}/payments",
                params=params,
                headers=_headers(),
                timeout=10,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise HTTPException(502, f"Erro ao listar cobranças: {e}")
        data = resp.json()
        for p in data.get("data") or []:
            cid = p.get("customer")
            nome, tel = _get_customer(cid) if cid else (None, None)
            cobrancas.append(
                {
                    "id": p.get("id"),
                    "customer": cid,
                    "nome": nome,
                    "telefone": tel,
                    "valor": p.get("value"),
                    "descricao": p.get("description"),
                    "vencimento": p.get("dueDate"),
                    "status": p.get("status"),
                }
            )
        if data.get("hasMore"):
            offset += data.get("limit", 100)
        else:
            break
    return {"cobrancas": cobrancas}


@router.delete("/{payment_id}")
def remover_cobranca(payment_id: str):
    try:
        resp = requests.delete(
            f"{ASAAS_BASE_URL}/payments/{payment_id}",
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(502, f"Erro ao remover cobrança: {e}")
    return {"status": "removido"}


@router.put("/{payment_id}")
def editar_cobranca(payment_id: str, dados: dict):
    payload = {}
    if "vencimento" in dados or "dueDate" in dados:
        payload["dueDate"] = dados.get("vencimento") or dados.get("dueDate")
    if "valor" in dados or "value" in dados:
        payload["value"] = dados.get("valor") or dados.get("value")
    if "descricao" in dados or "description" in dados:
        payload["description"] = dados.get("descricao") or dados.get("description")
    if not payload:
        raise HTTPException(400, "Nenhum campo para atualização informado")
    try:
        resp = requests.post(
            f"{ASAAS_BASE_URL}/payments/{payment_id}",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(502, f"Erro ao editar cobrança: {e}")
    return resp.json() if resp.content else {"status": "atualizado"}
