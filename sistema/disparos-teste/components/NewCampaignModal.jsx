import React, { useState } from 'https://esm.sh/react@18.2.0';
import { motion } from 'https://cdn.jsdelivr.net/npm/framer-motion@10.12.16/+esm';
import { parseCSV } from '../utils/parseCSV.js';

export default function NewCampaignModal({ onClose, onCreate }) {
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [file, setFile] = useState(null);
  const [schedule, setSchedule] = useState('');
  const [delay, setDelay] = useState(30);

  const valid = name && message && file && delay >= 30;

  const handleSubmit = async () => {
    const numbers = await parseCSV(file);
    const contacts = numbers.map(n => ({ numero: n, status: 'Pendente', data: null, resposta: null }));
    const camp = { id: Date.now(), name, message, contacts, status: 'Agendado', schedule, delay };
    onCreate(camp);
    onClose();
  };

  return (
    <motion.div className="fixed inset-0 bg-black/60 flex items-center justify-center">
      <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="bg-gray-800 p-6 rounded-lg w-full max-w-md">
        <h2 className="text-xl font-bold mb-4">Nova Campanha</h2>
        <div className="space-y-4">
          <input value={name} onChange={e => setName(e.target.value)} className="w-full p-2 rounded bg-gray-700" placeholder="Nome da campanha" />
          <div>
            <textarea value={message} onChange={e => setMessage(e.target.value)} className="w-full p-2 rounded bg-gray-700" rows="3" maxLength="500" placeholder="Mensagem padrão"></textarea>
            <p className="text-xs text-right">{message.length}/500</p>
          </div>
          <input type="file" accept=".csv" onChange={e => setFile(e.target.files[0])} className="w-full" />
          <input type="datetime-local" value={schedule} onChange={e => setSchedule(e.target.value)} className="w-full p-2 rounded bg-gray-700" />
          <input type="number" min="30" value={delay} onChange={e => setDelay(Number(e.target.value))} className="w-full p-2 rounded bg-gray-700" placeholder="Delay (segundos)" />
        </div>
        <div className="mt-4 flex justify-end space-x-2">
          <button onClick={onClose} className="px-4 py-2 bg-gray-600 rounded">Cancelar</button>
          <button disabled={!valid} onClick={handleSubmit} className="px-4 py-2 bg-green-600 disabled:opacity-50 rounded">Agendar disparo</button>
        </div>
      </motion.div>
    </motion.div>
  );
}
