import React, { useState } from 'https://esm.sh/react@18.2.0';
import { motion, AnimatePresence } from 'https://cdn.jsdelivr.net/npm/framer-motion@10.12.16/+esm';

export default function CampaignList({ campaigns, onSelect, onCancel }) {
  const [expanded, setExpanded] = useState(null);
  return (
    <div className="space-y-4">
      <AnimatePresence>
        {campaigns.map(c => (
          <motion.div key={c.id} layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="bg-gray-800 p-4 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <h3 className="font-semibold text-lg">{c.name}</h3>
                <p className="text-sm text-gray-400">{c.contacts.length} contatos</p>
                <p className="mt-2 text-sm">
                  {expanded === c.id ? c.message : c.message.slice(0,100)}
                  {c.message.length > 100 && (
                    <button className="ml-2 text-green-400" onClick={() => setExpanded(expanded === c.id ? null : c.id)}>
                      {expanded === c.id ? 'ver menos' : 'ver mais'}
                    </button>
                  )}
                </p>
                <p className="mt-1 text-xs">Status: {c.status}</p>
              </div>
              <div className="space-x-2">
                <button onClick={() => onSelect(c)} className="px-3 py-1 bg-blue-600 hover:bg-blue-700 rounded text-sm">Ver detalhes</button>
                {c.status === 'Agendado' || c.status === 'Enviando' ? (
                  <button onClick={() => onCancel(c.id)} className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-sm">Cancelar</button>
                ) : null}
              </div>
            </div>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
