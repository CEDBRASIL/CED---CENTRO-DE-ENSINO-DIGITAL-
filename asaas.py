import os
import logging
from datetime import date
from dateutil.relativedelta import relativedelta
from typing import List

import requests
from fastapi import APIRouter, HTTPException, Request

from utils import formatar_numero_whatsapp, parse_valor
from matricular import realizar_matricula, _buscar_aluno_id_por_cpf
from cursos import CURSOS_OM
import msgasaas

# Conjunto com todos os IDs de cursos válidos, usado para validar
# o campo `externalReference` recebido no webhook
VALID_CURSO_IDS = {cid for ids in CURSOS_OM.values() for cid in ids}

router = APIRouter(prefix="/asaas", tags=["Matrícula Assas"])

# A chave do ASAAS é lida dinamicamente em cada requisição para evitar
# problemas caso as variáveis de ambiente sejam carregadas depois do import.
ASAAS_KEY = os.getenv("ASAAS_KEY")
ASAAS_BASE_URL = os.getenv("ASAAS_BASE_URL", "https://api.asaas.com/v3")

# Endpoint da API do WhatsApp
WHATSAPP_URL = os.getenv(
    "WHATSAPP_URL", "https://whatsapptest-stij.onrender.com/send"
)
SENHA_PADRAO = os.getenv("SENHA_PADRAO", "123456")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _headers() -> dict:
    # Lê a chave diretamente do ambiente em cada chamada
    key = os.getenv("ASAAS_KEY")
    if not key:
        raise HTTPException(500, "ASAAS_KEY não configurada")
    return {"Content-Type": "application/json", "access_token": key}


def _criar_ou_obter_cliente(
    nome: str,
    cpf: str,
    phone: str,
    email: str | None = None,
    nascimento: str | None = None,
) -> str:
    payload = {"name": nome, "cpfCnpj": cpf, "mobilePhone": phone}
    if email:
        payload["email"] = email
    if nascimento:
        payload["birthDate"] = nascimento
    try:
        r = requests.post(
            f"{ASAAS_BASE_URL}/customers", json=payload, headers=_headers(), timeout=10
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"Erro de conexão: {e}")

    if r.status_code == 409:
        s = requests.get(
            f"{ASAAS_BASE_URL}/customers?cpfCnpj={cpf}",
            headers=_headers(),
            timeout=10,
        )
        if s.ok and s.json().get("data"):
            cid = s.json()["data"][0]["id"]
            logger.info("Cliente existente encontrado: %s", cid)
            return cid
        raise HTTPException(s.status_code, s.text)
    if r.ok:
        cid = r.json().get("id")
        logger.info("Novo cliente criado: %s", cid)
        return cid
    raise HTTPException(r.status_code, r.text)


def obter_cliente_por_cpf(cpf: str) -> str | None:
    """Retorna o ID do cliente ASAAS a partir do CPF informado."""
    try:
        resp = requests.get(
            f"{ASAAS_BASE_URL}/customers",
            params={"cpfCnpj": cpf},
            headers=_headers(),
            timeout=10,
        )
        if resp.ok:
            dados = resp.json().get("data") or []
            if dados:
                return dados[0].get("id")
    except requests.RequestException as e:
        logger.exception("Erro ao buscar cliente por CPF: %s", e)
    return None


def cancelar_assinaturas_por_cpf(cpf: str) -> int:
    """Cancela todas as assinaturas ativas de um cliente pelo CPF."""
    cid = obter_cliente_por_cpf(cpf)
    if not cid:
        logger.info("Nenhum cliente ASAAS encontrado para o CPF %s", cpf)
        return 0

    try:
        subs = requests.get(
            f"{ASAAS_BASE_URL}/subscriptions",
            params={"customer": cid},
            headers=_headers(),
            timeout=10,
        )
        subs.raise_for_status()
    except requests.RequestException as e:
        logger.exception("Erro ao listar assinaturas: %s", e)
        return 0

    dados = subs.json().get("data") or []
    canceladas = 0
    for sub in dados:
        sid = sub.get("id")
        if not sid:
            continue
        try:
            r = requests.delete(
                f"{ASAAS_BASE_URL}/subscriptions/{sid}",
                headers=_headers(),
                timeout=10,
            )
            if r.ok:
                canceladas += 1
            else:
                logger.warning(
                    "Falha ao cancelar assinatura %s: HTTP %s | %s",
                    sid,
                    r.status_code,
                    r.text,
                )
        except requests.RequestException as e:
            logger.exception("Erro ao cancelar assinatura %s: %s", sid, e)
    return canceladas


def _enviar_whatsapp(nome: str, phone: str, login: str, modulo: str) -> None:
    mensagem = (
        f"🎉 Bem-vindo à CED BRASIL!\n"
        f"Seu pagamento foi confirmado e sua matrícula está ativa!\n"
        f"LOGIN: {login}\n"
        f"SENHA: {SENHA_PADRAO}\n"
        f"MODULO ADQUIRIDO: {modulo}\n"
        f"Acesse o portal em 👉 www.cedbrasilia.com.br (clique em ENTRAR)\n"
        f"ou baixe nosso app:\n\n"
        f"📱 Android: https://play.google.com/store/apps/details?id=br.com.om.app&hl=pt_BR\n"
        f"🍎 iOS: https://apps.apple.com/br/app/meu-app-de-cursos/id1581898914\n\n"
        f"🚀 Bons estudos! Qualquer dúvida, conte com a nossa equipe!"
    )
    try:
        r = requests.get(
            WHATSAPP_URL,
            params={"para": formatar_numero_whatsapp(phone), "mensagem": mensagem},
            timeout=10,
        )
        r.raise_for_status()
        logger.info("WhatsApp enviado para %s", phone)
    except Exception:
        logger.exception("Erro ao enviar mensagem via WhatsApp")


def _enviar_whatsapp_checkout(nome: str, phone: str, url: str) -> None:
    mensagem = (
        f"👋 Olá {nome}, tudo bem?\n\n"
        f"Segue o link para pagamento do seu curso: {url}\n"
        "Assim que o pagamento for confirmado, enviaremos seus dados de acesso via WhatsApp.\n\n"
        "Qualquer dúvida, estou à disposição para ajudar!"
    )
    try:
        r = requests.get(
            WHATSAPP_URL,
            params={"para": formatar_numero_whatsapp(phone), "mensagem": mensagem},
            timeout=10,
        )
        r.raise_for_status()
        logger.info("WhatsApp de checkout enviado para %s", phone)
    except Exception:
        logger.exception("Erro ao enviar mensagem de checkout via WhatsApp")


def _criar_checkout(
    nome: str,
    cpf: str,
    phone: str,
    valor: float,
    email: str | None = None,
    nascimento: str | None = None,
    descricao: str = "Curso",
    cursos_ids: List[int] | None = None,
    billing_type: str | None = None,
    callback_url: str | None = None,
    redirect_url: str | None = None,
    enviar_whatsapp: bool = True,
) -> dict:
    """Cria cobrança única no ASAAS e envia o link via WhatsApp.

    Defina ``enviar_whatsapp=False`` para apenas gerar o link sem disparar a
    mensagem automática.
    """
    cursos_ids = cursos_ids or []
    billing_type = billing_type or os.getenv("ASAAS_BILLING_TYPE", "UNDEFINED")

    valor = parse_valor(valor)

    if not nome or not cpf or not phone or valor is None:
        raise HTTPException(400, "Campos obrigatórios ausentes")
    if valor <= 0:
        raise HTTPException(400, "Valor inválido")

    if cpf and _buscar_aluno_id_por_cpf(cpf):
        raise HTTPException(409, "CPF já matriculado")

    customer_id = _criar_ou_obter_cliente(nome, cpf, phone, email, nascimento)

    payload = {
        "customer": customer_id,
        "billingType": billing_type,
        "value": valor,
        "description": descricao,
        "dueDate": date.today().isoformat(),
        "externalReference": ",".join(map(str, cursos_ids)),
    }
    if callback_url:
        payload["callbackUrl"] = callback_url
    if redirect_url:
        payload["redirectUrl"] = redirect_url

    try:
        r = requests.post(
            f"{ASAAS_BASE_URL}/payments",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"Erro de conexão: {e}")

    if not r.ok:
        raise HTTPException(r.status_code, r.text)

    data = r.json()
    url = (
        data.get("chargeUrl")
        or data.get("invoiceUrl")
        or data.get("bankSlipUrl")
        or data.get("transactionReceiptUrl")
    )

    if url and enviar_whatsapp:
        _enviar_whatsapp_checkout(nome, phone, url)

    return {"url": url, "customer": customer_id}


@router.post("/checkout")
def criar_assinatura(dados: dict, enviar_whatsapp: bool = True):
    nome = dados.get("nome")
    cpf = dados.get("cpf")
    phone = dados.get("whatsapp") or dados.get("phone")
    valor = parse_valor(dados.get("valor"))
    descricao = dados.get("descricao") or dados.get("curso") or "Curso"
    cursos_ids: List[int] = dados.get("cursos_ids") or []
    billing_type = dados.get("billingType")
    callback_url = os.getenv("ASAAS_CALLBACK_URL")
    redirect_url = os.getenv("ASAAS_REDIRECT_URL")

    # Permite sobrescrever via payload
    enviar_whatsapp = bool(dados.get("enviar_whatsapp", enviar_whatsapp))

    return _criar_checkout(
        nome,
        cpf,
        phone,
        valor,
        descricao,
        cursos_ids,
        billing_type,
        callback_url,
        redirect_url,
        enviar_whatsapp,
    )


@router.post("/matricula")
def gerar_matricula_checkout(dados: dict, enviar_whatsapp: bool = True):
    """Gera link de pagamento ao receber dados de matrícula."""
    nome = dados.get("nome")
    cpf = dados.get("cpf")
    phone = dados.get("whatsapp") or dados.get("phone")
    valor = parse_valor(dados.get("valor"))
    descricao = dados.get("descricao") or dados.get("curso") or "Curso"
    cursos_ids: List[int] = dados.get("cursos_ids") or []
    billing_type = dados.get("billingType")
    callback_url = os.getenv("ASAAS_CALLBACK_URL")
    redirect_url = os.getenv("ASAAS_REDIRECT_URL")

    return _criar_checkout(
        nome,
        cpf,
        phone,
        valor,
        descricao,
        cursos_ids,
        billing_type,
        callback_url,
        redirect_url,
        enviar_whatsapp,
    )


@router.post("/assinatura")
def criar_assinatura_recorrente(dados: dict, enviar_whatsapp: bool = True):
    """Cria uma assinatura no ASAAS e envia o link de pagamento opcionalmente."""
    nome = dados.get("nome")
    cpf = dados.get("cpf")
    phone = dados.get("whatsapp") or dados.get("phone")
    valor = parse_valor(dados.get("valor"))
    descricao = dados.get("descricao") or "Assinatura"
    cursos_ids: List[int] = dados.get("cursos_ids") or []
    billing_type = dados.get("billingType") or os.getenv(
        "ASAAS_BILLING_TYPE", "UNDEFINED"
    )
    cycle = dados.get("ciclo") or dados.get("cycle") or "MONTHLY"
    next_due = (
        dados.get("dueDate") or (date.today() + relativedelta(months=1)).isoformat()
    )
    callback_url = os.getenv("ASAAS_CALLBACK_URL")
    redirect_url = os.getenv("ASAAS_REDIRECT_URL")

    if not nome or not cpf or not phone or valor is None:
        raise HTTPException(400, "Campos obrigatórios ausentes")
    if valor <= 0:
        raise HTTPException(400, "Valor inválido")

    if cpf and _buscar_aluno_id_por_cpf(cpf):
        raise HTTPException(409, "CPF já matriculado")

    customer_id = _criar_ou_obter_cliente(nome, cpf, phone, dados.get("email"), dados.get("nascimento"))
    logger.info("Cliente ASAAS %s criado/obtido para %s", customer_id, phone)

    payload = {
        "customer": customer_id,
        "billingType": billing_type,
        "value": valor,
        "cycle": cycle,
        "nextDueDate": next_due,
        "description": descricao,
        "externalReference": ",".join(map(str, cursos_ids)),
    }
    if callback_url:
        payload["callbackUrl"] = callback_url
    if redirect_url:
        payload["redirectUrl"] = redirect_url

    try:
        r = requests.post(
            f"{ASAAS_BASE_URL}/subscriptions",
            json=payload,
            headers=_headers(),
            timeout=10,
        )
    except requests.RequestException as e:
        raise HTTPException(502, f"Erro de conexão: {e}")

    if not r.ok:
        raise HTTPException(r.status_code, r.text)

    data = r.json()
    url = (
        data.get("chargeUrl")
        or data.get("invoiceUrl")
        or data.get("bankSlipUrl")
        or data.get("transactionReceiptUrl")
    )

    if url and enviar_whatsapp:
        logger.info("Enviando link de checkout para %s", phone)
        _enviar_whatsapp_checkout(nome, phone, url)

    if enviar_whatsapp:
        try:
            msgasaas.enviar_link_fatura(
                {
                    "nome": nome,
                    "whatsapp": phone,
                    "fatura_url": url,
                    "customer": customer_id,
                    "valor": valor,
                    "descricao": descricao,
                }
            )
        except Exception:
            logger.exception("Erro ao acionar msgasaas")

    logger.info(
        "Assinatura criada com sucesso para %s (customer=%s, subscription=%s)",
        nome,
        customer_id,
        data.get("id"),
    )
    return {
        "url": url,
        "customer": customer_id,
        "subscription": data.get("id"),
    }


