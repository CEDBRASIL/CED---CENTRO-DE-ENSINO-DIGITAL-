from datetime import datetime
from pydantic import BaseModel

class ListaBase(BaseModel):
    nome: str
    descricao: str | None = None

class ListaCreate(ListaBase):
    pass

class Lista(ListaBase):
    id: int
    criado_em: datetime
    class Config:
        orm_mode = True

class ContatoBase(BaseModel):
    lista_id: int | None = None
    nome: str | None = None
    telefone: str
    desc1: str | None = None
    desc2: str | None = None
    desc3: str | None = None

class ContatoCreate(ContatoBase):
    pass

class Contato(ContatoBase):
    id: int
    class Config:
        orm_mode = True

class Arquivo(BaseModel):
    id: int
    nome_original: str
    caminho: str
    criado_em: datetime
    class Config:
        orm_mode = True

class MensagemBase(BaseModel):
    identificador: str
    tipo: str
    conteudo: str | None = None
    arquivo_id: int | None = None

class MensagemCreate(MensagemBase):
    pass

class Mensagem(MensagemBase):
    id: int
    criado_em: datetime
    class Config:
        orm_mode = True

class DisparoCreate(BaseModel):
    lista_id: int
    mensagem_id: int
    agendado_para: datetime | None = None

class Disparo(BaseModel):
    id: int
    lista_id: int
    mensagem_id: int
    agendado_para: datetime | None
    status: str
    criado_em: datetime
    class Config:
        orm_mode = True
