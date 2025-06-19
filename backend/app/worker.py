import asyncio
import json
import random
from datetime import datetime
from sqlalchemy import select
from .models import AsyncSessionLocal, Disparo, Contato
from .models import engine, Base
from .routers.disparos import router  # ensure router imported

try:
    from disparos import enviar_mensagem as send_message
except Exception:  # pragma: no cover
    def send_message(numero, texto):
        print(f"[MOCK] {numero}: {texto}")

LOG_FILE = 'log.json'

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def worker_loop():
    await init_db()
    while True:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Disparo).where(
                    Disparo.status == 'pendente',
                    Disparo.agendado_para <= datetime.utcnow()
                )
            )
            disparos = result.scalars().all()
            for disp in disparos:
                contatos_res = await session.execute(
                    select(Contato).where(Contato.lista_id == disp.lista_id)
                )
                contatos = contatos_res.scalars().all()
                for contato in contatos:
                    send_message(contato.telefone, disp.mensagem.conteudo)
                    log_entry = {
                        'disparo_id': disp.id,
                        'numero': contato.telefone,
                        'horario': datetime.utcnow().isoformat()
                    }
                    _append_log(log_entry)
                    delay = 50 + random.randint(-10, 10)
                    if delay < 30:
                        delay = 30
                    await asyncio.sleep(delay)
                disp.status = 'concluido'
                await session.commit()
        await asyncio.sleep(5)

def _append_log(entry):
    log = []
    try:
        with open(LOG_FILE, 'r') as f:
            log = json.load(f)
    except FileNotFoundError:
        pass
    log.append(entry)
    with open(LOG_FILE, 'w') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
