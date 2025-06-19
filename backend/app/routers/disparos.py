from datetime import datetime
from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from ..models import AsyncSessionLocal, Disparo
from ..schemas import Disparo, DisparoCreate

router = APIRouter(prefix="/api/disparos", tags=["Disparos"])

@router.post("", response_model=Disparo)
async def criar(disparo: DisparoCreate):
    async with AsyncSessionLocal() as session:
        obj = Disparo(**disparo.dict(), status='pendente')
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

@router.get("", response_model=list[Disparo])
async def listar():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Disparo))
        return result.scalars().all()

@router.get("/{disp_id}", response_model=Disparo)
async def obter(disp_id: int):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Disparo, disp_id)
        if not obj:
            raise HTTPException(404)
        return obj

@router.delete("/{disp_id}")
async def remover(disp_id: int):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Disparo, disp_id)
        if not obj:
            raise HTTPException(404)
        await session.delete(obj)
        await session.commit()
    return {"ok": True}
