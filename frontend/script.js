const api = '/api';

async function uploadArquivo(){
    const f = document.getElementById('fileInput').files[0];
    if(!f) return;
    const fd = new FormData();
    fd.append('file', f);
    await fetch(`${api}/arquivos/upload`, {method:'POST', body:fd});
    listarArquivos();
}

async function criarLista(){
    const nome = document.getElementById('nomeLista').value;
    if(!nome) return;
    await fetch(`${api}/listas`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nome})});
    listarListas();
}

async function criarContato(){
    const tel = document.getElementById('contatoTelefone').value;
    const lista = parseInt(document.getElementById('contatoLista').value);
    await fetch(`${api}/contatos`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({telefone:tel, lista_id:lista})});
    listarContatos();
}

async function criarMensagem(){
    const ident = document.getElementById('msgIdent').value;
    const cont = document.getElementById('msgConteudo').value;
    await fetch(`${api}/mensagens`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identificador:ident, tipo:'texto', conteudo:cont})});
    listarMensagens();
}

async function criarDisparo(){
    const lista = parseInt(document.getElementById('dispLista').value);
    const msg = parseInt(document.getElementById('dispMsg').value);
    await fetch(`${api}/disparos`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({lista_id:lista, mensagem_id:msg})});
    listarDisparos();
}

async function listarArquivos(){
    const ul=document.getElementById('listaArquivos');
    const r=await fetch(`${api}/arquivos`);
    const dados=await r.json();
    ul.innerHTML=dados.map(a=>`<li>${a.id} - ${a.nome_original}</li>`).join('');
}

async function listarListas(){
    const ul=document.getElementById('listaListas');
    const r=await fetch(`${api}/listas`);
    const dados=await r.json();
    ul.innerHTML=dados.map(l=>`<li>${l.id} - ${l.nome}</li>`).join('');
}

async function listarContatos(){
    const ul=document.getElementById('listaContatos');
    const r=await fetch(`${api}/contatos`);
    const dados=await r.json();
    ul.innerHTML=dados.map(c=>`<li>${c.id} - ${c.telefone}</li>`).join('');
}

async function listarMensagens(){
    const ul=document.getElementById('listaMensagens');
    const r=await fetch(`${api}/mensagens`);
    const dados=await r.json();
    ul.innerHTML=dados.map(m=>`<li>${m.id} - ${m.identificador}</li>`).join('');
}

async function listarDisparos(){
    const ul=document.getElementById('listaDisparos');
    const r=await fetch(`${api}/disparos`);
    const dados=await r.json();
    ul.innerHTML=dados.map(d=>`<li>${d.id} - ${d.status}</li>`).join('');
}

document.addEventListener('DOMContentLoaded', ()=>{
    listarArquivos();
    listarListas();
    listarContatos();
    listarMensagens();
    listarDisparos();
});
