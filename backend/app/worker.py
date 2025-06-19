import asyncio
import json
import random
from datetime import datetime

from sqlalchemy import select, update

from .models import AsyncSessionLocal, Disparo, Contato, Mensagem, init_db

try:
    from disparos_service import enviar_mensagem as send_message  # type: ignore
except Exception:  # pragma: no cover - fallback
    def send_message(numero: str, texto: str):
        print(f"Mock send to {numero}: {texto}")

LOG_FILE = "log.json"

async def append_log(entry: dict):
    try:
        with open(LOG_FILE, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = []
    data.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def process_disparo(did: int):
    async with AsyncSessionLocal() as db:
        disp = await db.get(Disparo, did)
        if not disp:
            return
        await db.execute(update(Disparo).where(Disparo.id == did).values(status="enviando"))
        await db.commit()
        contatos = await db.execute(select(Contato).where(Contato.lista_id == disp.lista_id))
        contatos = contatos.scalars().all()
        mensagem = await db.get(Mensagem, disp.mensagem_id)

    for contato in contatos:
        send_message(contato.telefone, mensagem.conteudo)
        await append_log({
            "numero": contato.telefone,
            "disparo_id": did,
            "hora": datetime.utcnow().isoformat()
        })
        delay = max(30, 50 + random.randint(-10, 10))
        await asyncio.sleep(delay)

    async with AsyncSessionLocal() as db:
        await db.execute(update(Disparo).where(Disparo.id == did).values(status="concluido"))
        await db.commit()

async def worker_loop():
    await init_db()
    while True:
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                select(Disparo.id).where(
                    Disparo.status == "pendente",
                    (Disparo.agendado_para == None) | (Disparo.agendado_para <= datetime.utcnow())
                ).order_by(Disparo.id)
            )
            row = res.first()
        if row:
            await process_disparo(row[0])
        else:
            await asyncio.sleep(5)
