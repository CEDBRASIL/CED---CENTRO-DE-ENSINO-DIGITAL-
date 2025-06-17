const COURSE_PRICES = {
  "Excel PRO": 49.90,
  "Design Gráfico": 89.90,
  "Analista e Desenvolvimento de Sistemas": 79.90,
  "Administração": 49.90,
  "Inglês Fluente": 99.90,
  "Inglês Kids": 39.90,
  "Informática Essencial": 49.90,
  "Operador de Micro": 59.90,
  "Especialista em Marketing & Vendas 360º": 149.90,
  "Marketing Digital": 89.90,
  "Pacote Office": 29.99,
};

function applyCPFMask(v) {
  v = v.replace(/\D/g, '').slice(0,11);
  v = v.replace(/(\d{3})(\d)/, '$1.$2');
  v = v.replace(/(\d{3})(\d)/, '$1.$2');
  v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
  return v;
}

function applyWhatsappMask(value) {
  value = value.replace(/\D/g, '');
  if (value.length > 11) value = value.slice(0, 11);
  if (value.length > 10) {
    return `(${value.slice(0,2)}) ${value.slice(2,7)}-${value.slice(7)}`;
  } else if (value.length > 6) {
    return `(${value.slice(0,2)}) ${value.slice(2,6)}-${value.slice(6)}`;
  } else if (value.length > 2) {
    return `(${value.slice(0,2)}) ${value.slice(2)}`;
  } else {
    return value;
  }
}

function normalizarNumero(num) {
  num = String(num || '').replace(/\D/g, '');
  if (!num.startsWith('55')) num = '55' + num;
  if (num.startsWith('55') && num[4] === '9') {
    num = num.slice(0,4) + num.slice(5);
  }
  return num;
}

async function gerarLinkPagamento(dadosAluno) {
  const resposta = await fetch('https://api.cedbrasilia.com.br/asaas/checkout', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dadosAluno)
  });

  if (!resposta.ok) {
    throw new Error('Falha ao gerar cobrança');
  }

  const json = await resposta.json();
  if (json.url) {
    window.location.href = json.url;
  }
}

async function obterIdsCurso(nome) {
  try {
    const res = await fetch('https://api.cedbrasilia.com.br/cursos');
    const data = await res.json();
    return (data.cursos && data.cursos[nome]) ? data.cursos[nome] : [];
  } catch (_) {
    return [];
  }
}

function initCoursePage(courseName) {
  document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('currentYear').textContent = new Date().getFullYear();
    document.getElementById('course-title').textContent = courseName;
    const price = COURSE_PRICES[courseName] || 0;
    const priceEl = document.getElementById('course-price');
    if (priceEl) priceEl.textContent = price ? 'R$ ' + price.toFixed(2).replace('.', ',') : '';
    const courseIds = await obterIdsCurso(courseName);

    const nomeInput = document.getElementById('nome');
    const cpfInput = document.getElementById('cpf');
    const emailInput = document.getElementById('email');
    const phoneInput = document.getElementById('whatsapp');
    const message = document.getElementById('form-message');

    cpfInput.addEventListener('input', e => { e.target.value = applyCPFMask(e.target.value); });
    phoneInput.addEventListener('input', e => { e.target.value = applyWhatsappMask(e.target.value); });

    document.getElementById('enrollmentForm').addEventListener('submit', async e => {
      e.preventDefault();
      const nome = nomeInput.value.trim();
      const cpf = cpfInput.value.replace(/\D/g, '').slice(0,11);
      const email = emailInput.value.trim();
      const phone = normalizarNumero(phoneInput.value);
      if (!nome || !cpf || !email || !phone) {
        message.textContent = 'Preencha todos os campos.';
        message.className = 'text-center text-red-500 mt-2 h-5';
        return;
      }
      message.textContent = 'Enviando...';
      message.className = 'text-center text-gray-300 mt-2 h-5';
      try {
        await gerarLinkPagamento({
          nome,
          cpf,
          email,
          whatsapp: phone,
          valor: price,
          descricao: courseName,
          cursos_ids: courseIds
        });
      } catch (err) {
        message.textContent = err.message || 'Erro ao enviar. Tente novamente.';
        message.className = 'text-center text-red-500 mt-2 h-5';
      }
    });
  });
}
