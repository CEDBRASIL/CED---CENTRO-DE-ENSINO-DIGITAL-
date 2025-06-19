const api = '/api';

async function uploadArquivo() {
    const inp = document.getElementById('fileInput');
    if (!inp.files.length) return;
    const fd = new FormData();
    fd.append('file', inp.files[0]);
    await fetch(`${api}/arquivos`, {method:'POST', body:fd});
    inp.value='';
    carregarArquivos();
}

async function criarLista() {
    const nome = document.getElementById('listaNome').value;
    await fetch(`${api}/listas`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({nome})});
    document.getElementById('listaNome').value='';
    carregarListas();
}

async function criarMensagem() {
    const identificador = document.getElementById('msgIdent').value;
    const conteudo = document.getElementById('msgConteudo').value;
    await fetch(`${api}/mensagens`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({identificador,tipo:'texto',conteudo})});
    document.getElementById('msgIdent').value='';
    document.getElementById('msgConteudo').value='';
    carregarMensagens();
}

async function criarDisparo() {
    const lista_id = parseInt(document.getElementById('dispLista').value);
    const mensagem_id = parseInt(document.getElementById('dispMsg').value);
    const agendado_para = document.getElementById('dispQuando').value;
    await fetch(`${api}/disparos`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({lista_id,mensagem_id,agendado_para})});
    carregarDisparos();
}

async function carregarArquivos() {
    const r = await fetch(`${api}/arquivos`);
    const dados = await r.json();
    const ul = document.getElementById('listaArquivos');
    ul.innerHTML='';
    dados.forEach(a=>{
        const li=document.createElement('li');
        li.textContent=`${a.id} - ${a.nome_original}`;
        ul.appendChild(li);
    });
}

async function carregarListas() {
    const r = await fetch(`${api}/listas`);
    const dados = await r.json();
    const ul = document.getElementById('listaListas');
    ul.innerHTML='';
    dados.forEach(l=>{
        const li=document.createElement('li');
        li.textContent=`${l.id} - ${l.nome}`;
        ul.appendChild(li);
    });
}

async function carregarMensagens() {
    const r = await fetch(`${api}/mensagens`);
    const dados = await r.json();
    const ul = document.getElementById('listaMensagens');
    ul.innerHTML='';
    dados.forEach(m=>{
        const li=document.createElement('li');
        li.textContent=`${m.id} - ${m.identificador}`;
        ul.appendChild(li);
    });
}

async function carregarDisparos() {
    const r = await fetch(`${api}/disparos`);
    const dados = await r.json();
    const ul = document.getElementById('listaDisparos');
    ul.innerHTML='';
    dados.forEach(d=>{
        const li=document.createElement('li');
        li.textContent=`${d.id} - ${d.status}`;
        ul.appendChild(li);
    });
}

carregarArquivos();
carregarListas();
carregarMensagens();
carregarDisparos();
