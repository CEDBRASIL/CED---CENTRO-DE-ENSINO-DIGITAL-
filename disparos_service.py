import os
import json
import random
import asyncio
from datetime import datetime
from threading import Thread

from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd

app = Flask(__name__)


def get_conn():
    return psycopg2.connect(
        host=os.getenv('PG_HOST'),
        port=os.getenv('PG_PORT'),
        dbname=os.getenv('PG_DB'),
        user=os.getenv('PG_USER'),
        password=os.getenv('PG_PASS'),
        sslmode='require'
    )


@app.route('/grupos')
def grupos():
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute('SELECT DISTINCT grupo FROM contatos')
        grupos = [r[0] for r in cur.fetchall() if r[0]]
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

def load_log():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r') as f:
            return json.load(f)
    return []

def save_log(log):
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def is_on_whatsapp(numero: str) -> bool:
    return random.random() > 0.1


def enviar_mensagem(numero: str, mensagem: str):
    print(f'Enviando para {numero}: {mensagem}')


async def envio_async(grupos):
    with get_conn() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        if grupos:
            cur.execute('SELECT nome, numero, grupo FROM contatos WHERE grupo = ANY(%s)', (grupos,))
        else:
            cur.execute('SELECT nome, numero, grupo FROM contatos')
        contatos = cur.fetchall()
        cur.execute('SELECT conteudo FROM mensagens WHERE ativa=true')
        msgs = [r['conteudo'] for r in cur.fetchall()]
    log = load_log()
    enviados = {e['numero'] for e in log}
    total = len(log)
    for c in contatos:
        numero = c['numero']
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
        delay_base = max(30, 50 + random.randint(-50, 50))
        delay = delay_base + random.randint(0,10)
        for i in range(delay, 0, -1):
            print(f'{numero} - msg "{mensagem[:10]}..." aguardando {i}s - total {total}', end='\r')
            await asyncio.sleep(1)
        print()


def iniciar_envio(grupos):
    asyncio.run(envio_async(grupos))


@app.route('/enviar', methods=['POST'])
def enviar():
    grupos = request.json.get('grupos', [])
    Thread(target=iniciar_envio, args=(grupos,)).start()
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)

