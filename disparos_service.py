import os
import json
import random
import asyncio
from datetime import datetime
from threading import Thread
from typing import Iterable, Optional
import urllib.parse
import requests

from utils import formatar_numero_whatsapp

from flask import Flask, request, jsonify
import pandas as pd

app = Flask(__name__)

# Endpoints da API do WhatsApp
WHATSAPP_URL = os.getenv(
    "WHATSAPP_URL", "https://whatsapptest-stij.onrender.com/send"
)
WP_API = os.getenv("WP_API", "https://whatsapptest-stij.onrender.com")


# Arquivos locais para armazenamento
CONTACTS_FILE = "contatos.json"
MESSAGES_FILE = "mensagens.json"


def load_contacts() -> list[dict]:
    try:
        with open(CONTACTS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_contacts(data: list[dict]) -> None:
    with open(CONTACTS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_messages() -> list[dict]:
    try:
        with open(MESSAGES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_messages(data: list[dict]) -> None:
    with open(MESSAGES_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


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
    contatos = load_contacts()
    grupos = sorted({c.get('grupo') for c in contatos if c.get('grupo')})
    return jsonify({'grupos': grupos})


@app.route('/grupos/<string:nome>')
def grupo_detalhe(nome: str):
    """Retorna participantes de um grupo específico."""
    participantes = buscar_numeros_do_grupo(nome)
    return jsonify({
        'nome': nome,
        'quantidade': len(participantes),
        'participantes': [{'numero': n} for n in participantes]
    })


@app.route('/mensagens', methods=['GET', 'POST'])
def mensagens():
    if request.method == 'POST':
        data = request.get_json()
        msgs = load_messages()
        new_id = max([m.get('id', 0) for m in msgs], default=0) + 1
        msgs.append({
            'id': new_id,
            'conteudo': data['conteudo'],
            'tipo': data.get('tipo', 'texto'),
            'ativa': True
        })
        save_messages(msgs)
        return jsonify({'id': new_id})
    else:
        return jsonify(load_messages())


@app.route('/mensagens/<int:mid>', methods=['PATCH', 'DELETE'])
def mensagem_det(mid):
    if request.method == 'PATCH':
        ativa = request.get_json().get('ativa', True)
        msgs = load_messages()
        for m in msgs:
            if m.get('id') == mid:
                m['ativa'] = ativa
                break
        save_messages(msgs)
        return jsonify({'ok': True})
    else:
        msgs = [m for m in load_messages() if m.get('id') != mid]
        save_messages(msgs)
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
        records.append({'nome': row.get('nome'), 'numero': numero, 'grupo': row.get('grupo')})
    contatos = load_contacts()
    existentes = {c['numero'] for c in contatos}
    novos = [r for r in records if r['numero'] not in existentes]
    contatos.extend(novos)
    save_contacts(contatos)
    return jsonify({'importados': len(novos)})


# ------------- Log helpers -------------
LOG_FILE = 'log.json'
HISTORY_FILE = 'history.json'

PROGRESS = {
    'status': 'parado',  # parado | disparando | pausado | concluido | abortado
    'total': 0,
    'enviados': 0,
    'grupos': [],
    'inicio': None,
    'fim': None
}

ABORTAR = False
PAUSAR = False
LIMITE_DIARIO = int(os.getenv('LIMITE_DIARIO', '0'))

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
    """Realiza o envio sequencial de mensagens com controle de progresso."""
    global PROGRESS, ABORTAR, PAUSAR
    grupos = list(grupos or [])
    numeros = list(numeros or [])
    contatos = []
    if grupos:
        for g in grupos:
            for n in buscar_numeros_do_grupo(g):
                contatos.append({'nome': None, 'numero': n, 'grupo': g})
    else:
        contatos = load_contacts()
    contatos.extend({'nome': None, 'numero': n, 'grupo': None} for n in numeros)
    msgs = [m['conteudo'] for m in load_messages() if m.get('ativa')]
    random.shuffle(contatos)
    log = load_log()
    enviados = {e['numero'] for e in log}
    PROGRESS.update(status='disparando', total=len(contatos), enviados=0, grupos=grupos, inicio=datetime.utcnow().isoformat(), fim=None)
    total = len(log)
    primeira = True
    for c in contatos:
        while PAUSAR and not ABORTAR:
            PROGRESS.update(status='pausado')
            await asyncio.sleep(1)
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
        if LIMITE_DIARIO and PROGRESS['enviados'] >= LIMITE_DIARIO:
            PAUSAR = True
            PROGRESS.update(status='pausado')
            break
        if primeira:
            primeira = False
        else:
            delay_base = max(30, 50 + random.randint(-50, 50))
            delay = delay_base + random.randint(0, 10)
            for i in range(delay, 0, -1):
                print(f'{numero} - msg "{mensagem[:10]}..." aguardando {i}s - total {total}', end='\r')
                await asyncio.sleep(1)
            print()
    if PROGRESS['status'] not in ('abortado', 'pausado'):
        PROGRESS.update(status='concluido', fim=datetime.utcnow().isoformat())


def iniciar_envio(grupos, numeros):
    global ABORTAR, PAUSAR
    ABORTAR = False
    PAUSAR = False
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


@app.post('/pause')
def pausar():
    """Pausa temporariamente o disparo."""
    global PAUSAR
    PAUSAR = True
    PROGRESS.update(status='pausado')
    return jsonify({'ok': True})


@app.post('/resume')
def continuar():
    """Continua um disparo pausado."""
    global PAUSAR
    PAUSAR = False
    if PROGRESS['status'] == 'pausado':
        PROGRESS['status'] = 'disparando'
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

