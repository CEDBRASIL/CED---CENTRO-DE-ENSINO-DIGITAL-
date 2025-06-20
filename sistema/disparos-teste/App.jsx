import React, { useState } from 'https://esm.sh/react@18.2.0';
import CampaignList from './components/CampaignList.jsx';
import NewCampaignModal from './components/NewCampaignModal.jsx';
import CampaignDetails from './components/CampaignDetails.jsx';

export default function App() {
  const [campaigns, setCampaigns] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [selected, setSelected] = useState(null);

  const addCampaign = (camp) => setCampaigns((prev) => [...prev, camp]);
  const cancelCampaign = (id) => setCampaigns((prev) => prev.map(c => c.id === id ? { ...c, status: 'Cancelado' } : c));

  return (
    <div className="min-h-screen p-4 relative">
      {selected ? (
        <CampaignDetails campaign={selected} onBack={() => setSelected(null)} />
      ) : (
        <>
          <h1 className="text-2xl font-bold mb-4">Campanhas de Disparo (Teste)</h1>
          <CampaignList campaigns={campaigns} onSelect={setSelected} onCancel={cancelCampaign} />
          <button
            onClick={() => setShowModal(true)}
            className="fixed bottom-6 right-6 bg-green-600 hover:bg-green-700 transition-colors text-white p-4 rounded-full shadow-lg"
          >
            + Nova campanha
          </button>
        </>
      )}
      {showModal && (
        <NewCampaignModal onClose={() => setShowModal(false)} onCreate={addCampaign} />
      )}
    </div>
  );
}
