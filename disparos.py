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
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

from utils import formatar_numero_whatsapp

router = APIRouter()

# Endpoints da API do WhatsApp
WHATSAPP_URL = "https://whatsapptest-stij.onrender.com/send"
WP_API = "https://whatsapptest-stij.onrender.com"


def get_conn():
    return psycopg2.connect(
        host=os.getenv('PG_HOST'),
        port=os.getenv('PG_PORT'),
        dbname=os.getenv('PG_DB'),
        user=os.getenv('PG_USER'),
        password=os.getenv('PG_PASS'),
        sslmode='require',
    )


# ─────────────────────────────────────────────────────────────
# Função utilitária para garantir que as tabelas existam
# ─────────────────────────────────────────────────────────────
def ensure_tables() -> None:
    """Cria as tabelas necessárias caso não existam."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS listas (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                descricao TEXT
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS contatos (
                id SERIAL PRIMARY KEY,
                nome TEXT,
                numero TEXT UNIQUE,
                grupo TEXT,
                lista_id INTEGER REFERENCES listas(id)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS mensagens (
                id SERIAL PRIMARY KEY,
                titulo TEXT,
                conteudo TEXT NOT NULL,
                tipo TEXT DEFAULT 'texto',
                ativa BOOLEAN DEFAULT TRUE
            )
            """
        )
        # colunas extras caso a base exista sem as novas modificações
        cur.execute("ALTER TABLE contatos ADD COLUMN IF NOT EXISTS lista_id INTEGER REFERENCES listas(id)")
        cur.execute("ALTER TABLE mensagens ADD COLUMN IF NOT EXISTS titulo TEXT")
        conn.commit()


# Garante que as tabelas sejam criadas quando o módulo é importado
ensure_tables()


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


@router.get('/listas')
def listar_listas():
    """Retorna todas as listas de contatos."""
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT l.*, COUNT(c.id) AS total FROM listas l '
            'LEFT JOIN contatos c ON c.lista_id=l.id GROUP BY l.id ORDER BY l.id'
        )
        return cur.fetchall()


@router.post('/listas')
def criar_lista(data: dict):
    nome = data.get('nome')
    if not nome:
        raise HTTPException(400, 'Nome obrigatorio')
    desc = data.get('descricao')
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            'INSERT INTO listas (nome, descricao) VALUES (%s,%s) RETURNING id',
            (nome, desc)
        )
        lid = cur.fetchone()[0]
        conn.commit()
    return {'id': lid}


@router.delete('/listas/{lid}')
def deletar_lista(lid: int):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('DELETE FROM contatos WHERE lista_id=%s', (lid,))
        cur.execute('DELETE FROM listas WHERE id=%s', (lid,))
        conn.commit()
    return {'ok': True}


@router.get('/listas/{lid}/contatos')
def listar_contatos(lid: int):
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            'SELECT id, nome, numero FROM contatos WHERE lista_id=%s ORDER BY id',
            (lid,)
        )
        return cur.fetchall()


@router.post('/listas/{lid}/contatos')
def adicionar_contatos(lid: int, contatos: list[dict]):
    if not contatos:
        raise HTTPException(400, 'Contatos obrigatorios')
    with get_conn() as conn, conn.cursor() as cur:
        for c in contatos:
            cur.execute(
                'INSERT INTO contatos (nome, numero, grupo, lista_id) '
                'VALUES (%s,%s,%s,%s) ON CONFLICT (numero) DO NOTHING',
                (c.get('nome'), c.get('numero'), c.get('grupo'), lid)
            )
        conn.commit()
    return {'adicionados': len(contatos)}


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
    titulo = data.get('titulo')
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            'INSERT INTO mensagens (titulo, conteudo, tipo, ativa) VALUES (%s,%s,%s,true) RETURNING id',
            (titulo, conteudo, tipo),
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
    """Verifica o formato e simula checagem no WhatsApp."""
    digitos = "".join(filter(str.isdigit, numero or ""))
    if not digitos.startswith("55") or len(digitos) != 12:
        return False
    return random.random() > 0.05


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
