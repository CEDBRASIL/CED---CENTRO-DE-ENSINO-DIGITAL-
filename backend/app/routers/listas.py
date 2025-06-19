from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from ..models import AsyncSessionLocal, Lista
from ..schemas import Lista, ListaCreate

router = APIRouter(prefix="/api/listas", tags=["Listas"])

@router.post("", response_model=Lista)
async def criar(lista: ListaCreate):
    async with AsyncSessionLocal() as session:
        obj = Lista(**lista.dict())
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

@router.get("", response_model=list[Lista])
async def listar():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Lista))
        return result.scalars().all()

@router.get("/{lista_id}", response_model=Lista)
async def obter(lista_id: int):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Lista, lista_id)
        if not obj:
            raise HTTPException(404)
        return obj

@router.put("/{lista_id}", response_model=Lista)
async def atualizar(lista_id: int, lista: ListaCreate):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Lista, lista_id)
        if not obj:
            raise HTTPException(404)
        for k, v in lista.dict().items():
            setattr(obj, k, v)
        await session.commit()
        await session.refresh(obj)
        return obj

@router.delete("/{lista_id}")
async def remover(lista_id: int):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Lista, lista_id)
        if not obj:
            raise HTTPException(404)
        await session.delete(obj)
        await session.commit()
    return {"ok": True}
