from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from ..models import AsyncSessionLocal, Mensagem
from ..schemas import Mensagem, MensagemCreate

router = APIRouter(prefix="/api/mensagens", tags=["Mensagens"])

@router.post("", response_model=Mensagem)
async def criar(mensagem: MensagemCreate):
    async with AsyncSessionLocal() as session:
        obj = Mensagem(**mensagem.dict())
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

@router.get("", response_model=list[Mensagem])
async def listar():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Mensagem))
        return result.scalars().all()

@router.put("/{msg_id}", response_model=Mensagem)
async def atualizar(msg_id: int, mensagem: MensagemCreate):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Mensagem, msg_id)
        if not obj:
            raise HTTPException(404)
        for k, v in mensagem.dict().items():
            setattr(obj, k, v)
        await session.commit()
        await session.refresh(obj)
        return obj

@router.delete("/{msg_id}")
async def remover(msg_id: int):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Mensagem, msg_id)
        if not obj:
            raise HTTPException(404)
        await session.delete(obj)
        await session.commit()
    return {"ok": True}
