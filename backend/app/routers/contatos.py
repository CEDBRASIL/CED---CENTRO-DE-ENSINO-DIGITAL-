import csv
from io import StringIO
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy import select
from ..models import AsyncSessionLocal, Contato
from ..schemas import Contato, ContatoCreate

router = APIRouter(prefix="/api/contatos", tags=["Contatos"])

@router.post("", response_model=Contato)
async def criar(contato: ContatoCreate):
    async with AsyncSessionLocal() as session:
        obj = Contato(**contato.dict())
        session.add(obj)
        await session.commit()
        await session.refresh(obj)
        return obj

@router.get("", response_model=list[Contato])
async def listar(lista_id: int | None = None):
    async with AsyncSessionLocal() as session:
        stmt = select(Contato)
        if lista_id:
            stmt = stmt.where(Contato.lista_id == lista_id)
        result = await session.execute(stmt)
        return result.scalars().all()

@router.put("/{contato_id}", response_model=Contato)
async def atualizar(contato_id: int, contato: ContatoCreate):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Contato, contato_id)
        if not obj:
            raise HTTPException(404)
        for k, v in contato.dict().items():
            setattr(obj, k, v)
        await session.commit()
        await session.refresh(obj)
        return obj

@router.delete("/{contato_id}")
async def remover(contato_id: int):
    async with AsyncSessionLocal() as session:
        obj = await session.get(Contato, contato_id)
        if not obj:
            raise HTTPException(404)
        await session.delete(obj)
        await session.commit()
    return {"ok": True}

@router.post("/upload/{lista_id}")
async def upload(lista_id: int, arquivo: UploadFile = File(...)):
    data = await arquivo.read()
    text = data.decode('utf-8')
    reader = csv.DictReader(StringIO(text))
    contatos = []
    for row in reader:
        numero = row.get('telefone') or row.get('numero')
        if not numero:
            continue
        contatos.append(
            Contato(
                lista_id=lista_id,
                nome=row.get('nome'),
                telefone=numero,
                desc1=row.get('desc1'),
                desc2=row.get('desc2'),
                desc3=row.get('desc3')
            )
        )
    async with AsyncSessionLocal() as session:
        session.add_all(contatos)
        await session.commit()
    return {"importados": len(contatos)}
