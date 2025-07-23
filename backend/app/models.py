import os
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = os.getenv('PG_PORT', '5432')
PG_DB = os.getenv('PG_DB', 'ced')
PG_USER = os.getenv('PG_USER', 'ced')
PG_PASS = os.getenv('PG_PASS', 'ced')

PG_SSLROOTCERT = os.getenv('PG_SSLROOTCERT', '/etc/ssl/certs/ca-certificates.crt')

DB_URL = (
    f"postgresql+asyncpg://{PG_USER}:{PG_PASS}@{PG_HOST}:{PG_PORT}/{PG_DB}"
    f"?sslmode=require&sslrootcert={PG_SSLROOTCERT}"
)

engine = create_async_engine(DB_URL, future=True, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()

class Lista(Base):
    __tablename__ = 'listas'
    id = Column(Integer, primary_key=True)
    nome = Column(Text, nullable=False)
    descricao = Column(Text)
    criado_em = Column(DateTime, server_default=func.now())
    contatos = relationship('Contato', back_populates='lista')
    disparos = relationship('Disparo', back_populates='lista')

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
    criado_em = Column(DateTime, server_default=func.now())

class Mensagem(Base):
    __tablename__ = 'mensagens'
    id = Column(Integer, primary_key=True)
    identificador = Column(Text, nullable=False)
    tipo = Column(Text, nullable=False)
    conteudo = Column(Text)
    arquivo_id = Column(Integer, ForeignKey('arquivos.id'))
    criado_em = Column(DateTime, server_default=func.now())
    arquivo = relationship('Arquivo')
    disparos = relationship('Disparo', back_populates='mensagem')

class Disparo(Base):
    __tablename__ = 'disparos'
    id = Column(Integer, primary_key=True)
    lista_id = Column(Integer, ForeignKey('listas.id'))
    mensagem_id = Column(Integer, ForeignKey('mensagens.id'))
    agendado_para = Column(DateTime)
    status = Column(Text, default='pendente')
    criado_em = Column(DateTime, server_default=func.now())
    lista = relationship('Lista', back_populates='disparos')
    mensagem = relationship('Mensagem', back_populates='disparos')

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
