import os
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime

PG_HOST = os.getenv('PG_HOST')
PG_PORT = os.getenv('PG_PORT')
PG_DB = os.getenv('PG_DB')
PG_USER = os.getenv('PG_USER')
PG_PASS = os.getenv('PG_PASS')

DATABASE_URL = (
    f"postgresql+asyncpg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

class Lista(Base):
    __tablename__ = 'listas'
    id = Column(Integer, primary_key=True)
    nome = Column(Text, nullable=False)
    descricao = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)
    contatos = relationship('Contato', back_populates='lista', cascade='all, delete')
    disparos = relationship('Disparo', back_populates='lista', cascade='all, delete')

class Contato(Base):
    __tablename__ = 'contatos'
    id = Column(Integer, primary_key=True)
    lista_id = Column(Integer, ForeignKey('listas.id'))
    nome = Column(Text)
    telefone = Column(Text, nullable=False)
    desc1 = Column(Text)
    desc2 = Column(Text)
    desc3 = Column(Text)
    lista = relationship('Lista', back_populates='contatos')

class Arquivo(Base):
    __tablename__ = 'arquivos'
    id = Column(Integer, primary_key=True)
    nome_original = Column(Text)
    caminho = Column(Text)
    criado_em = Column(DateTime, default=datetime.utcnow)

class Mensagem(Base):
    __tablename__ = 'mensagens'
    id = Column(Integer, primary_key=True)
    identificador = Column(Text, nullable=False)
    tipo = Column(Text, nullable=False)
    conteudo = Column(Text)
    arquivo_id = Column(Integer, ForeignKey('arquivos.id'))
    criado_em = Column(DateTime, default=datetime.utcnow)
    arquivo = relationship('Arquivo')
    disparos = relationship('Disparo', back_populates='mensagem', cascade='all, delete')

class Disparo(Base):
    __tablename__ = 'disparos'
    id = Column(Integer, primary_key=True)
    lista_id = Column(Integer, ForeignKey('listas.id'))
    mensagem_id = Column(Integer, ForeignKey('mensagens.id'))
    agendado_para = Column(DateTime)
    status = Column(Text, default='pendente')
    criado_em = Column(DateTime, default=datetime.utcnow)
    lista = relationship('Lista', back_populates='disparos')
    mensagem = relationship('Mensagem', back_populates='disparos')
