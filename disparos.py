import os
import json
import random
import asyncio
from datetime import datetime
from threading import Thread
from typing import Iterable
import urllib.parse
import requests

import phonenumbers
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import time
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from utils import formatar_numero_whatsapp

router = APIRouter()

# Endpoints da API do WhatsApp
WHATSAPP_URL = os.getenv(
    "WHATSAPP_URL", "https://whatsapptest-stij.onrender.com/send"
)
WP_API = os.getenv("WP_API", "https://whatsapptest-stij.onrender.com")


def get_conn(connect_timeout: int = 5):
    """Abre conexão usando ``DATABASE_URL`` ou variáveis separadas."""
    db_url = os.getenv("DATABASE_URL")
    conn_kwargs = dict(
        connect_timeout=connect_timeout,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
        options="-c statement_timeout=60000 -c idle_in_transaction_session_timeout=30000",
    )
    if db_url:
        if "sslmode" not in db_url:
            sep = "&" if "?" in db_url else "?"
            db_url += f"{sep}sslmode=require"
        return psycopg2.connect(db_url, **conn_kwargs)
    return psycopg2.connect(
        host=os.getenv("DB_HOST", os.getenv("PG_HOST")),
        port=os.getenv("DB_PORT", os.getenv("PG_PORT", "5432")),
        dbname=os.getenv("DB_NAME", os.getenv("PG_DB")),
        user=os.getenv("DB_USER", os.getenv("PG_USER")),
        password=os.getenv("DB_PASSWORD", os.getenv("PG_PASS")),
        sslmode="require",
        sslrootcert=os.getenv("PG_SSLROOTCERT", "/etc/ssl/certs/ca-certificates.crt"),
        **conn_kwargs,
    )


def wait_for_db(max_attempts: int = 5, base_delay: float = 1.0) -> None:
    """Tenta conectar ao banco até ``max_attempts`` com backoff exponencial."""
    for attempt in range(1, max_attempts + 1):
        try:
            with get_conn() as conn, conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
            return
        except Exception as exc:  # pragma: no cover - log and retry
            logging.warning("DB connection failed (%s/%s): %s", attempt, max_attempts, exc)
            if attempt == max_attempts:
                raise
            time.sleep(base_delay * 2 ** (attempt - 1))


# ─────────────────────────────────────────────────────────────
# Função utilitária para garantir que as tabelas existam
# ─────────────────────────────────────────────────────────────
def ensure_tables() -> None:
    """Cria as tabelas necessárias caso não existam."""
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS contatos (
                    id SERIAL PRIMARY KEY,
                    nome TEXT,
                    numero TEXT UNIQUE,
                    grupo TEXT
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS mensagens (
                    id SERIAL PRIMARY KEY,
                    conteudo TEXT NOT NULL,
                    tipo TEXT DEFAULT 'texto',
                    ativa BOOLEAN DEFAULT TRUE
                )
                """
            )
            conn.commit()
    except Exception as exc:  # pragma: no cover - log
        logging.error("Erro ao criar tabelas: %s", exc)


def check_db() -> bool:
    """Executa SELECT 1 para verificar a conexão com o banco."""
    try:
        with get_conn(connect_timeout=2) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        return True
    except Exception:
        return False



# As tabelas são criadas no evento de startup em main.py


def buscar_numeros_do_grupo(nome: str) -> list[str]:
    """Obtém os números participantes de um grupo via API externa."""
    try:
        url = f"{WP_API}/grupos/{urllib.parse.quote(nome)}"
        resp = requests.get(url, timeout=10)
        if resp.ok:
            data = resp.json()
            return [p.get("numero") for p in data.get("participantes", [])]
    except Exception:
        pass
    return []


@router.get('/grupos')
def grupos():
    """Retorna a lista de grupos diretamente da API do WhatsApp."""
    try:
        resp = requests.get(f"{WP_API}/grupos", timeout=10)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    # Fallback para grupos registrados localmente
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT TRIM(grupo) AS grupo "
            "FROM contatos WHERE grupo IS NOT NULL ORDER BY 1"
        )
        grupos = [r[0] for r in cur.fetchall()]
    return {'grupos': grupos}


@router.get('/grupos/{nome}')
def grupo_detalhe(nome: str):
    """Retorna participantes de um grupo específico."""
    participantes = buscar_numeros_do_grupo(nome)
    return {
        'nome': nome,
        'quantidade': len(participantes),
        'participantes': [{'numero': n} for n in participantes]
    }


@router.get('/mensagens')
def listar_mensagens():
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT * FROM mensagens')
        return cur.fetchall()


@router.post('/mensagens')
def criar_mensagem(data: dict):
    conteudo = data.get('conteudo')
    if not conteudo:
        raise HTTPException(400, 'Conteudo obrigatório')
    tipo = data.get('tipo', 'texto')
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            'INSERT INTO mensagens (conteudo, tipo, ativa) VALUES (%s,%s,true) RETURNING id',
            (conteudo, tipo),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
    return {'id': new_id}


@router.patch('/mensagens/{mid}')
def ativar_mensagem(mid: int, payload: dict):
    ativa = payload.get('ativa', True)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('UPDATE mensagens SET ativa=%s WHERE id=%s', (ativa, mid))
        conn.commit()
    return {'ok': True}


@router.delete('/mensagens/{mid}')
def deletar_mensagem(mid: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('DELETE FROM mensagens WHERE id=%s', (mid,))
        conn.commit()
    return {'ok': True}


@router.post('/import')
async def importar(file: UploadFile = File(...)):
    filename = file.filename.lower()
    if filename.endswith('.csv'):
        df = pd.read_csv(file.file)
    else:
        df = pd.read_excel(file.file)
    records = []
    for _, row in df.iterrows():
        numero = str(row.get('numero') or row.get('Numero') or '').strip()
        if not numero:
            continue
        records.append((row.get('nome'), numero, row.get('grupo')))
    with get_conn() as conn, conn.cursor() as cur:
        for r in records:
            cur.execute(
                'INSERT INTO contatos (nome, numero, grupo) VALUES (%s,%s,%s) ON CONFLICT (numero) DO NOTHING',
                r,
            )
        conn.commit()
    return {'importados': len(records)}


LOG_FILE = 'log.json'
HISTORY_FILE = 'history.json'

PROGRESS = {
    'status': 'parado',
    'total': 0,
    'enviados': 0,
    'grupos': [],
    'inicio': None,
    'fim': None,
}

ABORTAR = False


def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return []


def save_log(log):
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return []


def save_history(hist):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)


def is_on_whatsapp(numero: str) -> bool:
    """Valida somente o formato do número para envio no WhatsApp."""
    digitos = "".join(filter(str.isdigit, numero or ""))
    return digitos.startswith("55") and len(digitos) == 12


def enviar_mensagem(numero: str, mensagem: str):
    """Envia a mensagem utilizando o endpoint HTTP do WhatsApp."""
    try:
        requests.get(
            WHATSAPP_URL,
            params={"para": numero, "mensagem": mensagem},
            timeout=10,
        )
    except Exception:
        pass


async def envio_async(grupos: Iterable[str] | None = None, numeros: Iterable[str] | None = None):
    global PROGRESS, ABORTAR
    grupos = list(grupos or [])
    numeros = list(numeros or [])

    contatos = []
    if grupos:
        for g in grupos:
            for n in buscar_numeros_do_grupo(g):
                contatos.append({'nome': None, 'numero': n, 'grupo': g})
    else:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT nome, numero, grupo FROM contatos')
            contatos = cur.fetchall()

    contatos.extend({'nome': None, 'numero': n, 'grupo': None} for n in numeros)

    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute('SELECT conteudo FROM mensagens WHERE ativa=true')
        msgs = [r['conteudo'] for r in cur.fetchall()]
    random.shuffle(contatos)
    log = load_log()
    enviados = {e['numero'] for e in log}
    PROGRESS.update(status='disparando', total=len(contatos), enviados=0, grupos=grupos, inicio=datetime.utcnow().isoformat(), fim=None)
    total = len(log)
    primeira = True
    for c in contatos:
        if ABORTAR:
            PROGRESS.update(status='abortado', fim=datetime.utcnow().isoformat())
            break
        numero = formatar_numero_whatsapp(c['numero'])
        if numero in enviados:
            continue
        if not is_on_whatsapp(numero):
            log.append({'numero': numero, 'mensagem': None, 'horario': datetime.utcnow().isoformat(), 'status': 'invalido'})
            save_log(log)
            continue
        mensagem = random.choice(msgs)
        enviar_mensagem(numero, mensagem)
        log.append({'numero': numero, 'mensagem': mensagem, 'horario': datetime.utcnow().isoformat(), 'status': 'enviado'})
        save_log(log)
        total += 1
        PROGRESS['enviados'] += 1
        if primeira:
            primeira = False
        else:
            delay_base = max(30, 50 + random.randint(-50, 50))
            delay = delay_base + random.randint(0, 10)
            for _ in range(delay):
                await asyncio.sleep(1)
    if PROGRESS['status'] != 'abortado':
        PROGRESS.update(status='concluido', fim=datetime.utcnow().isoformat())


def iniciar_envio(grupos, numeros):
    global ABORTAR
    ABORTAR = False
    asyncio.run(envio_async(grupos, numeros))
    hist = load_history()
    hist.append({
        'grupos': grupos,
        'total': PROGRESS.get('total'),
        'enviados': PROGRESS.get('enviados'),
        'status': PROGRESS.get('status'),
        'inicio': PROGRESS.get('inicio'),
        'fim': PROGRESS.get('fim')
    })
    save_history(hist)


@router.post('/enviar')
def enviar(payload: dict):
    grupos = payload.get('grupos', [])
    numeros = payload.get('numeros', [])
    Thread(target=iniciar_envio, args=(grupos, numeros)).start()
    return {'ok': True}


# Rota mantida por compatibilidade com a versão antiga do sistema
@router.post('/disparo')
def disparo(payload: dict):
    """Alias para ``/enviar``."""
    return enviar(payload)


@router.get('/status')
def status():
    return JSONResponse(PROGRESS)


@router.post('/abort')
def abortar():
    global ABORTAR
    ABORTAR = True
    return {'ok': True}


@router.get('/historico')
def historico():
    return JSONResponse(load_history())


@router.get('/log')
def log():
    return JSONResponse(load_log())
