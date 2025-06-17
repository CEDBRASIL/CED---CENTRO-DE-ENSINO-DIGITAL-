document.addEventListener('DOMContentLoaded', async () => {
  const courseList = document.getElementById('course-list');
  if (!courseList) return;

  const descriptions = {
    'Excel PRO': 'Domine planilhas e crie relat\u00f3rios avan\u00e7ados para impulsionar sua produtividade.',
    'Design Gr\u00e1fico': 'Aprenda t\u00e9cnicas profissionais de cria\u00e7\u00e3o visual e destaque-se no mercado.',
    'Analista e Desenvolvimento de Sistemas': 'Forma\u00e7\u00e3o completa para quem deseja programar e projetar sistemas de alta qualidade.',
    'Administra\u00e7\u00e3o': 'Construa habilidades essenciais para gerenciar neg\u00f3cios com efici\u00eancia.',
    'Ingl\u00eas Fluente': 'Alcance a flu\u00eancia no idioma mais requisitado pelo mercado de trabalho.',
    'Ingl\u00eas Kids': 'Aulas divertidas e interativas para crian\u00e7as aprenderem ingl\u00eas brincando.',
    'Inform\u00e1tica Essencial': 'Conhecimentos fundamentais de inform\u00e1tica para o dia a dia.',
    'Operador de Micro': 'Tudo sobre operacionaliza\u00e7\u00e3o de computadores e pacote office.',
    'Especialista em Marketing & Vendas 360\u00ba': 'Estrat\u00e9gias de marketing e vendas para alavancar qualquer neg\u00f3cio.',
    'Marketing Digital': 'Domine as principais ferramentas de divulga\u00e7\u00e3o online.',
    'Pacote Office': 'Aprenda Word, Excel, PowerPoint e muito mais para o mercado.'
  };

  const details = {
    'Excel PRO': 'Curso completo para dominar planilhas, gráficos e automações no Excel, com foco em aplicações práticas.',
    'Design Gráfico': 'Aprenda a criar peças profissionais para web e impressão utilizando as principais ferramentas do mercado.',
    'Analista e Desenvolvimento de Sistemas': 'Formação abrangente em programação, análise de requisitos e desenvolvimento de sistemas de ponta a ponta.',
    'Administração': 'Capacitação em gestão empresarial, finanças e processos administrativos modernos.',
    'Inglês Fluente': 'Metodologia eficaz para alcançar fluência e se comunicar com confiança em qualquer situação.',
    'Inglês Kids': 'Conteúdo lúdico que estimula o aprendizado do idioma de forma divertida para crianças.',
    'Informática Essencial': 'Fundamentos de computação para uso pessoal e profissional, incluindo internet e segurança.',
    'Operador de Micro': 'Treinamento para operar computadores e dominar o pacote office no dia a dia.',
    'Especialista em Marketing & Vendas 360º': 'Estrategias avançadas para impulsionar vendas e posicionamento de marcas no ambiente digital.',
    'Marketing Digital': 'Domine redes sociais, anúncios pagos e SEO para atrair clientes online.',
    'Pacote Office': 'Do básico ao avançado em Word, Excel e PowerPoint com exercícios práticos.'
  };


  try {
    const res = await fetch('https://api.cedbrasilia.com.br/cursos');
    const data = await res.json();
    const cursos = data.cursos || {};

    let nomes = Object.keys(cursos).filter(n => n !== 'None');
    nomes.sort((a, b) => {
      if (a === 'Pacote Office') return -1;
      if (b === 'Pacote Office') return 1;
      return a.localeCompare(b);
    });

    nomes.forEach(name => {
      const desc = descriptions[name] || 'Curso profissionalizante do CED BRASIL.';
      const card = document.createElement('div');
      card.className = 'card p-6 flex flex-col justify-between';
      let badge = '';
      if (name === 'Pacote Office') {
        card.classList.add('border-2', 'border-green-500');
        badge = '<span class="bg-green-500 text-black px-2 py-1 rounded text-sm mb-2 inline-block">Recomendado</span>';
      }
      const priceVal = getCoursePrice(name);
      const price = `R$ ${priceVal.toFixed(2).replace('.', ',')}`;
      card.innerHTML = `
        <div>
          ${badge}
          <h3 class="text-xl font-bold mb-2">${name}</h3>
          <p class="text-gray-400 mb-4">${desc}</p>
          <p class="text-gray-400 mb-4">Valor: ${price}</p>
        </div>
        <div class="flex gap-2 mt-auto">
          <button class="details button-glow bg-spotify-green text-black font-bold px-4 py-2 rounded" data-name="${name}">Detalhes</button>
          <button class="enroll button-glow bg-blue-600 text-white font-bold px-4 py-2 rounded" data-name="${name}">Me matricular agora!</button>
        </div>
      `;
      const addBtn = card.querySelector('.enroll');
      const detailsBtn = card.querySelector('.details');
      addBtn.addEventListener('click', () => {
        window.location.href = `matricularasaas.html?curso=${encodeURIComponent(name)}`;
      });
      if (detailsBtn) {
        detailsBtn.addEventListener('click', () => {
          if (typeof showCourseModal === 'function') {
            showCourseModal(name, details[name] || desc);
          }
        });
      }
      courseList.appendChild(card);
    });
  } catch (err) {
    courseList.innerHTML = '<p class="text-gray-400">Erro ao carregar cursos.</p>';
  }
});
