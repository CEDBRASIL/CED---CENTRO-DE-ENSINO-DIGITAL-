import os
import json
import random
import asyncio
from datetime import datetime
from threading import Thread
from typing import Iterable, Optional
import urllib.parse
import requests

import phonenumbers
from utils import formatar_numero_whatsapp

from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd

app = Flask(__name__)

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
        sslmode='require'
    )


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


@app.route('/grupos')
def grupos():
    """Retorna a lista de grupos diretamente da API do WhatsApp."""
    try:
        resp = requests.get(f"{WP_API}/grupos", timeout=10)
        if resp.ok:
            return jsonify(resp.json())
    except Exception:
        pass
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT TRIM(grupo) AS grupo "
            "FROM contatos WHERE grupo IS NOT NULL ORDER BY 1"
        )
        grupos = [r[0] for r in cur.fetchall()]
    return jsonify({'grupos': grupos})


@app.route('/mensagens', methods=['GET', 'POST'])
def mensagens():
    if request.method == 'POST':
        data = request.get_json()
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                'INSERT INTO mensagens (conteudo, tipo, ativa) VALUES (%s,%s,true) RETURNING id',
                (data['conteudo'], data.get('tipo', 'texto'))
            )
            new_id = cur.fetchone()[0]
            conn.commit()
        return jsonify({'id': new_id})
    else:
        with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('SELECT * FROM mensagens')
            msgs = cur.fetchall()
        return jsonify(msgs)


@app.route('/mensagens/<int:mid>', methods=['PATCH', 'DELETE'])
def mensagem_det(mid):
    if request.method == 'PATCH':
        ativa = request.get_json().get('ativa', True)
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute('UPDATE mensagens SET ativa=%s WHERE id=%s', (ativa, mid))
            conn.commit()
        return jsonify({'ok': True})
    else:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute('DELETE FROM mensagens WHERE id=%s', (mid,))
            conn.commit()
        return jsonify({'ok': True})


@app.route('/import', methods=['POST'])
def importar():
    file = request.files['file']
    filename = file.filename.lower()
    if filename.endswith('.csv'):
        df = pd.read_csv(file)
    else:
        df = pd.read_excel(file)
    records = []
    for _, row in df.iterrows():
        numero = str(row.get('numero') or row.get('Numero') or '').strip()
        if not numero:
            continue
        records.append((row.get('nome'), numero, row.get('grupo')))
    with get_conn() as conn, conn.cursor() as cur:
        for r in records:
            cur.execute('INSERT INTO contatos (nome, numero, grupo) VALUES (%s,%s,%s) ON CONFLICT (numero) DO NOTHING', r)
        conn.commit()
    return jsonify({'importados': len(records)})


# ------------- Log helpers -------------
LOG_FILE = 'log.json'
HISTORY_FILE = 'history.json'

PROGRESS = {
    'status': 'parado',  # parado | disparando | concluido | abortado
    'total': 0,
    'enviados': 0,
    'grupos': [],
    'inicio': None,
    'fim': None
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
    # Simula 5% de números não encontrados no WhatsApp
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
    """Realiza o envio sequencial de mensagens com controle de progresso."""
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
            for i in range(delay, 0, -1):
                print(f'{numero} - msg "{mensagem[:10]}..." aguardando {i}s - total {total}', end='\r')
                await asyncio.sleep(1)
            print()
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


@app.route('/enviar', methods=['POST'])
def enviar():
    grupos = request.json.get('grupos', [])
    numeros = request.json.get('numeros', [])
    Thread(target=iniciar_envio, args=(grupos, numeros)).start()
    return jsonify({'ok': True})


# Compatibilidade com a rota antiga utilizada pelo frontend
@app.route('/disparo', methods=['POST'])
def disparo():
    """Alias para ``/enviar``."""
    return enviar()


@app.route('/status')
def status():
    """Retorna o progresso atual do disparo."""
    return jsonify(PROGRESS)


@app.post('/abort')
def abortar():
    """Solicita a interrupção do disparo em andamento."""
    global ABORTAR
    ABORTAR = True
    return jsonify({'ok': True})


@app.route('/historico')
def historico():
    return jsonify(load_history())


@app.route('/log')
def log():
    """Retorna o log atual de envios."""
    return jsonify(load_log())


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

