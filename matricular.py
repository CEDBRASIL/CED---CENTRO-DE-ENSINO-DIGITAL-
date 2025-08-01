import os
import threading
from typing import List, Tuple, Optional
import logging
import requests
from fastapi import APIRouter, HTTPException
from utils import formatar_numero_whatsapp
from datetime import datetime
from dateutil.relativedelta import relativedelta
from cursos import CURSOS_OM, obter_nomes_por_ids  # Importa o dicionário de mapeamento e utilitário

router = APIRouter()

# Variáveis de ambiente para OM
BASIC_B64 = os.getenv("BASIC_B64")
UNIDADE_ID = os.getenv("UNIDADE_ID")
OM_BASE = os.getenv("OM_BASE")

# Endpoint do WhatsApp (não requer token)
WHATSAPP_URL = os.getenv(
    "WHATSAPP_URL", "https://whatsapptest-stij.onrender.com/send"
)
# Número para receber logs via WhatsApp
WHATSAPP_LOG_NUM = os.getenv("WHATSAPP_LOG_NUM", "556186660241")

# ** Webhook do Discord para logs **
DISCORD_WEBHOOK_URL = os.getenv(
    "DISCORD_WEBHOOK_URL",
    "https://discord.com/api/webhooks/1377838283975036928/IgVvwyrBBWflKyXbIU9dgH4PhLwozHzrf-nJpj3w7dsZC-Ds9qN8_Toym3Tnbj-3jdU4",
)

# Prefixo para gerar CPFs sequenciais na OM
CPF_PREFIXO = "20254158"
cpf_lock = threading.Lock()

def _log(msg: str) -> None:
    """Registra mensagem no log padrão."""
    logging.info(msg)

def _obter_token_unidade() -> str:
    """
    Faz GET em /unidades/token/{UNIDADE_ID} para obter token da unidade na OM.
    """
    if not all([OM_BASE, BASIC_B64, UNIDADE_ID]):
        raise RuntimeError("Variáveis de ambiente OM não configuradas.")
    url = f"{OM_BASE}/unidades/token/{UNIDADE_ID}"
    r = requests.get(
        url,
        headers={"Authorization": f"Basic {BASIC_B64}"},
        timeout=8
    )
    if r.ok and r.json().get("status") == "true":
        return r.json()["data"]["token"]
    raise RuntimeError(f"Falha ao obter token da unidade: HTTP {r.status_code}")

def _total_alunos() -> int:
    """
    Retorna o total de alunos cadastrados na unidade OM (para gerar CPF).
    """
    url = f"{OM_BASE}/alunos/total/{UNIDADE_ID}"
    r = requests.get(
        url,
        headers={"Authorization": f"Basic {BASIC_B64}"},
        timeout=8
    )
    if r.ok and r.json().get("status") == "true":
        return int(r.json()["data"]["total"])

    # Fallback: busca todos que tenham CPF começando com o prefixo
    url2 = f"{OM_BASE}/alunos?unidade_id={UNIDADE_ID}&cpf_like={CPF_PREFIXO}"
    r2 = requests.get(
        url2,
        headers={"Authorization": f"Basic {BASIC_B64}"},
        timeout=8
    )
    if r2.ok and r2.json().get("status") == "true":
        return len(r2.json()["data"])

    raise RuntimeError("Falha ao apurar total de alunos")

# Melhorias na geração de CPF
CPF_MAX_RETRIES = 100  # Limite de tentativas para evitar colisões

def _proximo_cpf(incremento: int = 0) -> str:
    """
    Gera o próximo CPF sequencial, adicionando incremento para evitar colisões.
    """
    with cpf_lock:
        for tentativa in range(CPF_MAX_RETRIES):
            seq = _total_alunos() + 1 + incremento + tentativa
            cpf = CPF_PREFIXO + str(seq).zfill(3)
            if not _cpf_em_uso(cpf):
                return cpf
        raise RuntimeError("Limite de tentativas para gerar CPF excedido.")

def _cpf_em_uso(cpf: str) -> bool:
    """Verifica se o CPF já está em uso na base de dados da OM."""
    url = f"{OM_BASE}/alunos?unidade_id={UNIDADE_ID}&cpf={cpf}"
    r = requests.get(
        url,
        headers={"Authorization": f"Basic {BASIC_B64}"},
        timeout=8,
    )
    if r.ok and r.json().get("status") == "true":
        return len(r.json().get("data", [])) > 0
    return False


def _buscar_aluno_id_por_cpf(cpf: str) -> Optional[str]:
    """Retorna o ID do aluno cujo CPF já existe na OM (ou ``None``)."""
    url = f"{OM_BASE}/alunos?unidade_id={UNIDADE_ID}&cpf={cpf}"
    r = requests.get(
        url,
        headers={"Authorization": f"Basic {BASIC_B64}"},
        timeout=8,
    )
    if r.ok and r.json().get("status") == "true":
        dados = r.json().get("data", [])
        if dados:
            return str(dados[0].get("id"))
    return None

def _cadastrar_somente_aluno(
    nome: str,
    whatsapp: str,
    email: Optional[str],
    token_key: str,
    senha_padrao: str = "123456",
    cpf: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Cadastra apenas o aluno na OM (gera e-mail dummy se não for fornecido).
    Retorna: (aluno_id, cpf).
    """
    # Se não houver e-mail, cria um e-mail dummy a partir do WhatsApp
    email_validado = email or f"{whatsapp}@nao-informado.com"

    if cpf:
        existente = _buscar_aluno_id_por_cpf(cpf)
        if existente:
            return existente, cpf
        tentativas = 1
    else:
        tentativas = 60

    for tentativa in range(tentativas):
        cpf_atual = cpf or _proximo_cpf(tentativa)
        payload = {
            "token": token_key,
            "nome": nome,
            "email": email_validado,
            "whatsapp": whatsapp,
            "fone": whatsapp,
            "celular": whatsapp,
            "data_nascimento": "2000-01-01",
            "doc_cpf": cpf_atual,
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
            "senha": senha_padrao,
        }
        r = requests.post(
            f"{OM_BASE}/alunos",
            data=payload,
            headers={"Authorization": f"Basic {BASIC_B64}"},
            timeout=10
        )
        _log(
            f"[CAD] Tentativa {tentativa+1}/{tentativas} | Status {r.status_code} | Retorno OM: {r.text}"
        )

        if r.ok and r.json().get("status") == "true":
            aluno_id = r.json()["data"]["id"]
            return aluno_id, cpf_atual

        info = (r.json() or {}).get("info", "").lower()
        if "já está em uso" not in info or cpf:
            break

    raise RuntimeError("Falha ao cadastrar o aluno")

def _matricular_aluno_om(aluno_id: str, cursos_ids: List[int], token_key: str) -> bool:
    """
    Efetua a matrícula (vincula disciplinas) para o aluno já cadastrado.
    Se não houver cursos_ids, pula a matrícula e retorna True.
    """
    if not cursos_ids:
        _log(f"[MAT] Nenhum curso informado para aluno {aluno_id}. Pulando matrícula.")
        return True

    cursos_str = ",".join(map(str, cursos_ids))
    payload = {"token": token_key, "cursos": cursos_str}
    _log(f"[MAT] Matriculando aluno {aluno_id} nos cursos: {cursos_str}")
    r = requests.post(
        f"{OM_BASE}/alunos/matricula/{aluno_id}",
        data=payload,
        headers={"Authorization": f"Basic {BASIC_B64}"},
        timeout=10
    )
    sucesso = r.ok and r.json().get("status") == "true"
    _log(f"[MAT] {'✅' if sucesso else '❌'} Status {r.status_code} | Retorno OM: {r.text}")
    return sucesso

def _cadastrar_aluno_om(
    nome: str,
    whatsapp: str,
    email: Optional[str],
    cursos_ids: List[int],
    token_key: str,
    senha_padrao: str = "123456",
    cpf: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Cadastra aluno e, se houver cursos_ids, matricula nas disciplinas.
    Retorna: (aluno_id, cpf).
    """
    # 1) Cadastro básico do aluno
    aluno_id, cpf_result = _cadastrar_somente_aluno(
        nome, whatsapp, email, token_key, senha_padrao, cpf
    )

    # 2) Se houver cursos_ids, realiza a matrícula
    if cursos_ids:
        ok_matri = _matricular_aluno_om(aluno_id, cursos_ids, token_key)
        if not ok_matri:
            raise RuntimeError("Aluno cadastrado, mas falha ao matricular em disciplinas.")
    else:
        _log(f"[MAT] Curso não informado para {nome}. Cadastro concluído sem matrícula.")

    return aluno_id, cpf_result

def _send_whatsapp_chatpro(
    nome: str,
    whatsapp: str,
    cursos_nomes: List[str],
    cpf: str,
    senha_padrao: str = "123456",
    vencimento: str | None = None,
) -> None:
    """
    Envia mensagem automática no WhatsApp via ChatPro, com boas-vindas,
    informações de cursos e credenciais de acesso (CPF e senha).
    """
    # Novo endpoint não requer token ou configuração adicional

    # Formata e adiciona o DDI brasileiro caso ausente
    numero_telefone = formatar_numero_whatsapp(whatsapp)

    # Monta a mensagem com emojis e credenciais
    cursos_texto = "\n".join(f"• {c}" for c in cursos_nomes) if cursos_nomes else "Nenhum curso específico."
    mensagem = (
        f"👋 Olá, {nome}!\n\n"
        f"🎉 Seja bem-vindo(a) ao CED BRASIL!\n\n"
        f"📚 Curso(s) adquirido(s):\n"
        f"{cursos_texto}\n\n"
        f"🔐 Seu login: {cpf}\n"
        f"🔑 Sua senha: {senha_padrao}\n"
    )

    mensagem += (
        "\n💳 Link para iniciar a Assinatura: https://www.asaas.com/c/i4q17hkoxqmvdp90\n"
        "\n🌐 Portal do aluno: https://www.cedbrasilia.com.br/login\n"
        "🤖 APP Android: https://play.google.com/store/apps/datasafety?id=br.com.om.app&hl=pt_BR\n"
        "🍎 APP iOS: https://apps.apple.com/br/app/meu-app-de-cursos/id1581898914\n\n"
        "Qualquer dúvida, estamos à disposição. Boa jornada de estudos! 🚀"
    )

    # Envia a mensagem utilizando o novo endpoint
    try:
        r = requests.get(
            WHATSAPP_URL,
            params={"para": numero_telefone, "mensagem": mensagem},
            timeout=10
        )
        if r.ok:
            _log(f"[WHATSAPP] Mensagem enviada com sucesso para {numero_telefone}. Resposta: {r.text}")
        else:
            _log(f"[WHATSAPP] Falha ao enviar mensagem para {numero_telefone}. HTTP {r.status_code} | {r.text}")
    except Exception as e:
        _log(f"[WHATSAPP] Erro inesperado ao enviar WhatsApp para {numero_telefone}: {str(e)}")

def _send_whatsapp_log(mensagem: str) -> None:
    """Envia mensagem de log para o WhatsApp, exceto para renovação de token."""
    if "Token de unidade atualizado" in mensagem:
        return
    numero = formatar_numero_whatsapp(WHATSAPP_LOG_NUM)
    if not numero:
        return
    try:
        requests.get(
            WHATSAPP_URL,
            params={"para": numero, "mensagem": mensagem},
            timeout=10,
        )
    except Exception as e:
        _log(f"[WHATSAPP-LOG] Erro ao enviar log: {str(e)}")

def _send_discord_log(
    nome: str,
    cpf: str,
    whatsapp: str,
    cursos_ids: List[int],
    fatura_url: Optional[str] = None,
) -> None:
    """
    Envia mensagem de log para o canal Discord via webhook.
    Formato desejado:
    ✅ MATRÍCULA REALIZADA COM SUCESSO
    👤 Nome: Yuri Rodrigues de Sousa
    📄 CPF: 10539354120
    📱 Celular: +556186660241
    🎓 Cursos: [130, 599, 161, 160, 162]
    """
    if not DISCORD_WEBHOOK_URL:
        _log("⚠️ Webhook Discord não configurado. Pulando envio do log.")
        return

    # Formata a mensagem conforme o exemplo
    mensagem_discord = (
        "✅ MATRÍCULA REALIZADA COM SUCESSO\n\n"
        f"👤 Nome: {nome}\n"
        f"📄 CPF: {cpf}\n"
        f"📱 Celular: +{formatar_numero_whatsapp(whatsapp)}\n"
        f"🎓 Cursos: {cursos_ids}"
    )
    if fatura_url:
        mensagem_discord += f"\n🔗 Fatura: {fatura_url}"

    payload = {
        "content": mensagem_discord
    }

    _send_whatsapp_log(mensagem_discord)

    try:
        r = requests.post(
            DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10
        )
        if r.ok:
            _log(f"[DISCORD] Log enviado com sucesso. Resposta: {r.text}")
        else:
            _log(f"[DISCORD] Falha ao enviar log. HTTP {r.status_code} | {r.text}")
    except Exception as e:
        _log(f"[DISCORD] Erro inesperado ao enviar log: {str(e)}")

@router.post("/", summary="Cadastra (e opcionalmente matricula) um aluno na OM e envia WhatsApp via ChatPro")
async def realizar_matricula(dados: dict):
    """
    Espera um JSON com:
      - nome: str (obrigatório)
      - whatsapp: str (obrigatório)
      - email: str (opcional)
      - cursos: List[str] (opcional, nomes dos cursos conforme mapeamento em cursos.py)
      - cursos_ids: List[int] (opcional, IDs diretos, caso queira forçar)
      - fatura_url: str (opcional, link da fatura)
    """
    nome = dados.get("nome")
    whatsapp = dados.get("whatsapp")
    email = dados.get("email")
    cursos_nomes = dados.get("cursos") or []
    cursos_ids_input = dados.get("cursos_ids") or []
    fatura_url = dados.get("fatura_url") or dados.get("invoice_url")
    cpf = dados.get("cpf")

    if not nome or not whatsapp:
        raise HTTPException(
            status_code=400,
            detail="Dados incompletos: 'nome' e 'whatsapp' são obrigatórios."
        )

    cursos_ids: List[int] = []
    if cursos_ids_input:
        cursos_ids = cursos_ids_input
        if not cursos_nomes:
            cursos_nomes = obter_nomes_por_ids(cursos_ids_input)
    else:
        for nome_curso in cursos_nomes:
            chave = next((k for k in CURSOS_OM if k.lower() == nome_curso.lower()), None)
            if not chave:
                raise HTTPException(
                    status_code=404,
                    detail=f"Curso '{nome_curso}' não encontrado no mapeamento."
                )
            cursos_ids.extend(CURSOS_OM[chave])

    try:
        if cpf and _cpf_em_uso(cpf):
            _log(f"[MAT] CPF {cpf} já cadastrado. Pulando matrícula.")
            return {"status": "ja_matriculado", "cpf": cpf}

        # 1) obtém token da unidade OM
        token_unit = _obter_token_unidade()

        # 2) cadastra aluno e matricula
        aluno_id, cpf = _cadastrar_aluno_om(
            nome, whatsapp, email, cursos_ids, token_unit, cpf=cpf
        )

        # 3) envia mensagem automática no WhatsApp via ChatPro (agora com login e senha)
        venc = (datetime.now() + relativedelta(months=1)).strftime("%d/%m/%Y")
        _send_whatsapp_chatpro(nome, whatsapp, cursos_nomes, cpf, vencimento=venc)

        # 4) envia log para o Discord informando sucesso na matrícula
        _send_discord_log(nome, cpf, whatsapp, cursos_ids, fatura_url)

        return {
            "status": "ok",
            "aluno_id": aluno_id,
            "cpf": cpf,
            "disciplinas_matriculadas": cursos_ids,
        }

    except RuntimeError as e:
        _log(f"❌ Erro em /matricular: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        _log(f"❌ Erro inesperado em /matricular: {str(e)}")
        raise HTTPException(status_code=500, detail="Erro inesperado. Consulte os logs para mais detalhes.")
