import json
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException

from ..schemas import Mensagem as MensagemSchema, MensagemCreate

router = APIRouter(prefix="/api/mensagens", tags=["Mensagens"])

CACHE_FILE = os.getenv(
    "MENSAGENS_CACHE",
    os.path.join(os.path.dirname(__file__), "..", "mensagens_cache.json"),
)


def _load() -> list[dict]:
    try:
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def _save(data: list[dict]):
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _next_id(data: list[dict]) -> int:
    return max([m.get("id", 0) for m in data] or [0]) + 1


@router.post("", response_model=MensagemSchema)
async def criar(dados: MensagemCreate):
    msgs = _load()
    item = dados.dict()
    item["id"] = _next_id(msgs)
    item["criado_em"] = datetime.utcnow().isoformat()
    msgs.append(item)
    _save(msgs)
    return item


@router.get("", response_model=list[MensagemSchema])
async def listar():
    return _load()


@router.get("/{mid}", response_model=MensagemSchema)
async def detalhe(mid: int):
    msgs = _load()
    for m in msgs:
        if m["id"] == mid:
            return m
    raise HTTPException(404)


@router.put("/{mid}", response_model=MensagemSchema)
async def atualizar(mid: int, dados: MensagemCreate):
    msgs = _load()
    for m in msgs:
        if m["id"] == mid:
            m.update(dados.dict())
            _save(msgs)
            return m
    raise HTTPException(404)


@router.delete("/{mid}")
async def remover(mid: int):
    msgs = _load()
    new_msgs = [m for m in msgs if m["id"] != mid]
    if len(new_msgs) == len(msgs):
        raise HTTPException(404)
    _save(new_msgs)
    return {"ok": True}
