import os
import json
from datetime import datetime, timedelta, time
from typing import List, Dict
import requests
from fastapi import APIRouter, HTTPException

from matricular import _cadastrar_aluno_om, _obter_token_unidade
from bloquear import _alterar_bloqueio
from asaas import obter_cliente_por_cpf

router = APIRouter(prefix="/teste-gratis", tags=["Teste Gratuito"])

TRIAL_DAYS = 3
TRIALS_FILE = os.getenv("TRIALS_FILE", "trials.json")
SENHA_PADRAO = os.getenv("SENHA_PADRAO", "1234567")


def _load_trials() -> List[Dict]:
    if os.path.exists(TRIALS_FILE):
        try:
            with open(TRIALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_trials(trials: List[Dict]) -> None:
    with open(TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(trials, f, ensure_ascii=False, indent=2)


def _trial_end_date() -> datetime:
    return datetime.now() + timedelta(days=TRIAL_DAYS)


def _send_mensagem_teste(
    nome: str, whatsapp: str, curso: str, cpf: str, fim: str
) -> None:
    msg = (
        f"👋 Olá, {nome}!\n\n"
        f"🎉 Seja bem-vindo(a) ao CED BRASIL!\n\n"
        f"📚 Curso adquirido: {curso}\n\n"
        f"🔐 Seu login: {cpf}\n"
        f"🔑 Sua senha: {SENHA_PADRAO}\n\n"
        f"Fim do teste gratuito em: {fim}\n\n"
        "🌐 Portal do Aluno: https://www.cedbrasilia.com.br/login\n"
        "🤖 APP Android: https://play.google.com/store/apps/datasafety?id=br.com.om.app&hl=pt_BR\n"
        "🍎 APP iOS: https://apps.apple.com/br/app/meu-app-de-cursos/id1581898914"
    )
    try:
        requests.get(
            "https://whatsapptest-stij.onrender.com/send",
            params={"para": whatsapp, "mensagem": msg},
            timeout=10,
        )
    except Exception:
        pass


@router.post("")
def iniciar_teste(dados: dict):
    nome = dados.get("nome")
    whatsapp = dados.get("whatsapp")
    curso = dados.get("curso") or (dados.get("cursos") or [None])[0]
    cpf = dados.get("cpf")
    if not nome or not whatsapp or not curso:
        raise HTTPException(400, "Campos obrigatórios ausentes")
    try:
        token = _obter_token_unidade()
        aluno_id, cpf_res = _cadastrar_aluno_om(
            nome,
            whatsapp,
            None,
            [_id for _id in []],
            token,
            SENHA_PADRAO,
            cpf=cpf,
        )
        fim = _trial_end_date()
        data_fim = fim.strftime("%d/%m/%Y")
        _send_mensagem_teste(nome, whatsapp, curso, cpf_res, data_fim)
        trials = _load_trials()
        trials.append(
            {
                "aluno_id": aluno_id,
                "cpf": cpf_res,
                "whatsapp": whatsapp,
                "nome": nome,
                "curso": curso,
                "fim": fim.isoformat(),
                "notificado": False,
            }
        )
        _save_trials(trials)
        return {"status": "ok", "aluno_id": aluno_id, "cpf": cpf_res, "fim": data_fim}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/verificar")
def verificar_testes():
    agora = datetime.now()
    trials = _load_trials()
    atualizados = []
    for t in trials:
        if t.get("notificado"):
            atualizados.append(t)
            continue
        fim = datetime.fromisoformat(t["fim"])
        if agora >= datetime.combine(fim.date(), time(hour=7)):
            _enviar_cobranca(t)
            t["notificado"] = True
            if not _assinatura_ativa(t["cpf"]):
                try:
                    _alterar_bloqueio(t["aluno_id"], 1)
                except Exception:
                    pass
        atualizados.append(t)
    _save_trials(atualizados)
    return {"verificados": len(atualizados)}


def _enviar_cobranca(t: Dict) -> None:
    msg = f"Olá {t['nome']}, seu teste gratuito encerrou. Para continuar estudando, entre em contato e regularize o pagamento."
    try:
        requests.get(
            "https://whatsapptest-stij.onrender.com/send",
            params={"para": t["whatsapp"], "mensagem": msg},
            timeout=10,
        )
    except Exception:
        pass


def _assinatura_ativa(cpf: str) -> bool:
    cid = obter_cliente_por_cpf(cpf)
    if not cid:
        return False
    try:
        r = requests.get(
            f"{os.getenv('ASAAS_BASE_URL', 'https://api.asaas.com/v3')}/subscriptions",
            params={"customer": cid},
            headers={
                "Content-Type": "application/json",
                "access_token": os.getenv("ASAAS_KEY"),
            },
            timeout=10,
        )
        if r.ok:
            dados = r.json().get("data") or []
            for sub in dados:
                if sub.get("status") == "ACTIVE":
                    return True
    except Exception:
        pass
    return False
