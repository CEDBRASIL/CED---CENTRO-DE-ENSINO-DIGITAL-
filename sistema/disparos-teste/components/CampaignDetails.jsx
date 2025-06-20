import React from 'https://esm.sh/react@18.2.0';

export default function CampaignDetails({ campaign, onBack }) {
  const total = campaign.contacts.length;
  const enviados = campaign.contacts.filter(c => c.status === 'Enviado').length;
  const falhas = campaign.contacts.filter(c => c.status === 'Falhou').length;
  const pendentes = campaign.contacts.filter(c => c.status === 'Pendente').length;

  const exportCSV = () => {
    const rows = campaign.contacts.map(c => `${c.numero},${c.status},${c.data||''},${c.resposta||''}`);
    const csv = `numero,status,data,resposta\n${rows.join('\n')}`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${campaign.name}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <button onClick={onBack} className="mb-4 text-green-400">&larr; Voltar</button>
      <h2 className="text-xl font-bold mb-2">{campaign.name}</h2>
      <p className="mb-4">{campaign.message}</p>
      <div className="flex gap-4 mb-4">
        <span>Total: {total}</span>
        <span>Enviados: {enviados}</span>
        <span>Falhas: {falhas}</span>
        <span>Pendentes: {pendentes}</span>
      </div>
      <button onClick={exportCSV} className="mb-4 px-3 py-1 bg-green-600 rounded">Exportar CSV</button>
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left">
              <th className="px-2 py-1">Número</th>
              <th className="px-2 py-1">Status</th>
              <th className="px-2 py-1">Data/hora</th>
              <th className="px-2 py-1">Resposta</th>
            </tr>
          </thead>
          <tbody>
            {campaign.contacts.map((c, i) => (
              <tr key={i} className="border-t border-gray-700">
                <td className="px-2 py-1">{c.numero}</td>
                <td className="px-2 py-1">{c.status}</td>
                <td className="px-2 py-1">{c.data || '-'}</td>
                <td className="px-2 py-1">{c.resposta || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
