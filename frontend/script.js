const api = '/api';

async function fetchJSON(url, opts = {}) {
    const r = await fetch(url, opts);
    if (!r.ok) {
        const t = await r.text();
        throw new Error(t || 'Erro ao comunicar com servidor');
    }
    return r.json();
}

function showPage(id){
    document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));
    const pg = document.getElementById(id);
    if(pg) pg.classList.add('active');
    document.querySelectorAll('.vertical-nav-link').forEach(l=>{
        l.classList.toggle('active', l.dataset.page===id);
    });
    if(id==='page-add-contacts'){
        document.querySelector('.vertical-nav-link[data-page="page-contact-lists"]').classList.add('active');
    }else if(id==='page-add-template'){
        document.querySelector('.vertical-nav-link[data-page="page-messages"]').classList.add('active');
    }
    document.querySelector('.main-content').scrollTop=0;
}

async function listarListas(){
    const listas = await fetchJSON(`${api}/listas`);
    const tbody = document.getElementById('tbody-listas');
    tbody.innerHTML='';
    for(const lista of listas){
        const contatos = await fetchJSON(`${api}/contatos?lista_id=${lista.id}`);
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${lista.nome}</td>
            <td>${lista.descricao||''}</td>
            <td>${contatos.length}</td>
            <td class="table-actions">
                <button class="btn-icon btn-add-contacts" title="Adicionar Contatos" data-page="page-add-contacts" data-list-id="${lista.id}" data-list-name="${lista.nome}">➕</button>
                <button class="btn-icon btn-delete" title="Deletar Lista" data-del-list="${lista.id}">🗑️</button>
            </td>`;
        tbody.appendChild(tr);
    }
    document.querySelectorAll('[data-del-list]').forEach(btn=>{
        btn.addEventListener('click',async()=>{
            const id=btn.dataset.delList;
            await fetch(`${api}/listas/${id}`,{method:'DELETE'});
            listarListas();
        });
    });
    document.querySelectorAll('.btn-add-contacts').forEach(btn=>{
        btn.addEventListener('click',()=>{
            currentListId = btn.dataset.listId;
            document.getElementById('add-contacts-title').textContent=`Adicionar Contatos: ${btn.dataset.listName}`;
            showPage('page-add-contacts');
        });
    });
}

async function criarLista(nome, desc) {
    const resp = await fetch(`${api}/listas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nome, descricao: desc })
    });
    if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || 'Falha ao criar lista');
    }
}

async function listarMensagens(){
    const msgs = await fetchJSON(`${api}/mensagens`);
    const tbody = document.getElementById('tbody-mensagens');
    tbody.innerHTML='';
    for(const m of msgs){
        const prev = m.conteudo?m.conteudo.substring(0,40):'';
        const tr=document.createElement('tr');
        tr.innerHTML=`<td>${m.identificador}</td><td>${m.tipo}</td><td>${prev}</td><td class="table-actions"><button class="btn-icon" data-page="page-add-template" data-msg-id="${m.id}">✏️</button><button class="btn-icon btn-delete" data-del-msg="${m.id}">🗑️</button></td>`;
        tbody.appendChild(tr);
    }
    document.querySelectorAll('[data-del-msg]').forEach(b=>{
        b.addEventListener('click',async()=>{
            await fetch(`${api}/mensagens/${b.dataset.delMsg}`,{method:'DELETE'});
            listarMensagens();
            carregarSelects();
        });
    });
    document.querySelectorAll('[data-msg-id]').forEach(b=>{
        b.addEventListener('click',()=>{
            currentMsgId = b.dataset.msgId;
            showPage('page-add-template');
        });
    });
}

async function criarMensagem(data){
    await fetch(`${api}/mensagens`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
}

async function carregarSelects(){
    const listas = await fetchJSON(`${api}/listas`);
    const msgs = await fetchJSON(`${api}/mensagens`);
    const selList = document.getElementById('broadcast-list');
    const selMsg = document.getElementById('broadcast-template');
    selList.innerHTML=listas.map(l=>`<option value="${l.id}">${l.nome}</option>`).join('');
    selMsg.innerHTML=msgs.map(m=>`<option value="${m.id}">${m.identificador}</option>`).join('');
}

async function disparar(){
    const lista = document.getElementById('broadcast-list').value;
    const msg = document.getElementById('broadcast-template').value;
    const ag = document.getElementById('broadcast-schedule').value;
    const payload = {lista_id:parseInt(lista), mensagem_id:parseInt(msg)};
    if(ag) payload.agendado_para = ag;
    await fetch(`${api}/disparos`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
}

let currentListId = null;
let currentMsgId = null;
let gruposDados = [];
let gruposNome = '';

async function carregarGrupos(){
    const sel = document.getElementById('groups-select');
    sel.innerHTML = '<option>Carregando...</option>';
    try{
        const data = await fetchJSON('/grupos');
        const lista = data.grupos || data;
        sel.innerHTML = '<option value="">Selecione</option>';
        lista.forEach(g=>{
            const nome = typeof g === 'string' ? g : g.nome;
            const opt = document.createElement('option');
            opt.value = nome;
            opt.textContent = nome;
            sel.appendChild(opt);
        });
    }catch(e){
        sel.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

async function carregarParticipantes(nome){
    const tbody = document.getElementById('tbody-grupo');
    if(!nome){ tbody.innerHTML = ''; return; }
    tbody.innerHTML = '<tr><td colspan="2" style="text-align:center">Carregando...</td></tr>';
    try{
        const data = await fetchJSON(`/grupos/${encodeURIComponent(nome)}`);
        gruposNome = data.nome || nome;
        gruposDados = data.participantes || [];
        if(gruposDados.length===0){
            tbody.innerHTML = '<tr><td colspan="2" style="text-align:center">Nenhum número.</td></tr>';
        }else{
            tbody.innerHTML = gruposDados.map(p=>`<tr><td>${p.numero}</td><td>${p.admin?'Sim':'Não'}</td></tr>`).join('');
        }
    }catch(e){
        tbody.innerHTML = '<tr><td colspan="2" class="text-red-500" style="text-align:center">Erro ao carregar</td></tr>';
    }
}

function exportCSV(){
    if(gruposDados.length===0) return;
    const header = 'NOME,NUMERO,ADMIN\n';
    const rows = gruposDados.map(p=>`${gruposNome},${p.numero},${p.admin?'Sim':'Não'}`).join('\n');
    const blob = new Blob([header+rows],{type:'text/csv;charset=utf-8;'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'grupos.csv';
    a.click();
    URL.revokeObjectURL(url);
}

function exportXLSX(){
    if(gruposDados.length===0) return;
    const ws = XLSX.utils.json_to_sheet(gruposDados.map(p=>({NOME:gruposNome,NUMERO:p.numero,ADMIN:p.admin?'Sim':'Não'})));
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Grupos');
    const wbout = XLSX.write(wb,{bookType:'xlsx',type:'array'});
    const blob = new Blob([wbout],{type:'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'grupos.xlsx';
    a.click();
    URL.revokeObjectURL(url);
}

document.addEventListener('DOMContentLoaded', ()=>{
    listarListas();
    listarMensagens();
    carregarSelects();
    document.getElementById('btn-open-modal-add-list').addEventListener('click',()=>{
        document.getElementById('modal-add-list').style.display='flex';
    });
    document.querySelectorAll('.close-modal').forEach(b=>{
        b.addEventListener('click',()=>{ document.getElementById(b.dataset.modalId).style.display='none'; });
    });
    document.getElementById('modal-add-list').addEventListener('click',e=>{ if(e.target.id==='modal-add-list') e.currentTarget.style.display='none'; });
    document.getElementById('form-add-list').addEventListener('submit',async(e)=>{
        e.preventDefault();
        const nome = document.getElementById('list-name').value.trim();
        const desc = document.getElementById('list-desc').value.trim();
        if(!nome){
            alert('Informe o nome da lista');
            return;
        }
        try {
            await criarLista(nome, desc);
            document.getElementById('modal-add-list').style.display = 'none';
            listarListas();
            carregarSelects();
        } catch(err){
            alert(err.message);
        }
    });
    document.querySelectorAll('[data-page]').forEach(link=>{
        link.addEventListener('click',e=>{e.preventDefault();showPage(link.dataset.page);});
    });
    document.getElementById('msg-type').addEventListener('change',e=>{
        const isImg=e.target.value==='image';
        document.getElementById('image-upload-group').style.display=isImg?'block':'none';
        document.getElementById('preview-image').style.display=isImg?'block':'none';
    });
    document.getElementById('msg-content').addEventListener('input',e=>{
        document.getElementById('preview-text').textContent=e.target.value||'Sua mensagem aparecerá aqui.';
    });
    document.querySelectorAll('.btn-placeholder').forEach(btn=>{
        btn.addEventListener('click',()=>{
            const ta=document.getElementById('msg-content');
            const ph=btn.textContent;
            const start=ta.selectionStart; const end=ta.selectionEnd; const text=ta.value;
            ta.value = text.substring(0,start)+` ${ph} `+text.substring(end);
            ta.focus();
            ta.selectionStart=ta.selectionEnd=start+ph.length+2;
            ta.dispatchEvent(new Event('input',{bubbles:true}));
        });
    });
    document.getElementById('btn-criar-mensagem').addEventListener('click',async()=>{
        const data={identificador:document.getElementById('msg-identifier').value,
        tipo:document.getElementById('msg-type').value,
        conteudo:document.getElementById('msg-content').value};
        await criarMensagem(data);
        showPage('page-messages');
        listarMensagens();
        carregarSelects();
    });
    document.getElementById('btn-add-contato').addEventListener('click',async()=>{
        const nome=document.getElementById('contact-name').value;
        const tel=document.getElementById('contact-number').value;
        if(!currentListId) return;
        await fetch(`${api}/contatos`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({lista_id:parseInt(currentListId),nome,telefone:tel})});
        document.getElementById('contact-name').value='';
        document.getElementById('contact-number').value='';
    });
    document.getElementById('btn-import-contatos').addEventListener('click', async () => {
        const file = document.getElementById('file-contatos').files[0];
        if(!file || !currentListId){
            alert('Selecione o arquivo com os contatos');
            return;
        }
        const fd = new FormData();
        fd.append('file', file);
        try {
            await fetch(`${api}/contatos/importar/${currentListId}`, {method:'POST', body: fd});
            document.getElementById('file-contatos').value='';
            alert('Contatos importados com sucesso');
        } catch(e){
            alert('Falha ao importar contatos');
        }
    });
    document.getElementById('btn-disparar').addEventListener('click',async()=>{
        await disparar();
        alert('Disparo criado!');
    });
    document.querySelector('.file-input-wrapper').addEventListener('click',()=>{
        document.getElementById('file-upload').click();
    });
    document.getElementById('file-upload').addEventListener('change',async(e)=>{
        const f = e.target.files ? e.target.files[0] : null;
        if(!f || !currentListId) return;
        const fd = new FormData();
        fd.append('file', f);
        await fetch(`${api}/contatos/importar/${currentListId}`, {method:'POST', body: fd});
        e.target.value='';
        alert('Contatos importados com sucesso');
    });

    const grpSel = document.getElementById('groups-select');
    if(grpSel){
        carregarGrupos();
        grpSel.addEventListener('change',e=>carregarParticipantes(e.target.value));
    }
    const btnCsv = document.getElementById('btn-export-csv');
    if(btnCsv) btnCsv.addEventListener('click',exportCSV);
    const btnXlsx = document.getElementById('btn-export-xlsx');
    if(btnXlsx) btnXlsx.addEventListener('click',exportXLSX);
});
