from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AsyncSessionLocal, Lista
from ..schemas import Lista as ListaSchema, ListaCreate

router = APIRouter(prefix="/api/listas", tags=["Listas"])

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

@router.post("", response_model=ListaSchema)
async def criar(dados: ListaCreate, db: AsyncSession = Depends(get_db)):
    lista = Lista(**dados.dict())
    db.add(lista)
    await db.commit()
    await db.refresh(lista)
    return lista

@router.get("", response_model=list[ListaSchema])
async def listar(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lista))
    return res.scalars().all()

@router.get("/{lid}", response_model=ListaSchema)
async def detalhe(lid: int, db: AsyncSession = Depends(get_db)):
    lista = await db.get(Lista, lid)
    if not lista:
        raise HTTPException(404)
    return lista

@router.put("/{lid}", response_model=ListaSchema)
async def atualizar(lid: int, dados: ListaCreate, db: AsyncSession = Depends(get_db)):
    lista = await db.get(Lista, lid)
    if not lista:
        raise HTTPException(404)
    for k, v in dados.dict().items():
        setattr(lista, k, v)
    await db.commit()
    await db.refresh(lista)
    return lista

@router.delete("/{lid}")
async def remover(lid: int, db: AsyncSession = Depends(get_db)):
    lista = await db.get(Lista, lid)
    if not lista:
        raise HTTPException(404)
    await db.delete(lista)
    await db.commit()
    return {"ok": True}
