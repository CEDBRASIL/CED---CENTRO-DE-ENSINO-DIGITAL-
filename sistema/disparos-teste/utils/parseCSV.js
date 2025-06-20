import Papa from 'https://cdn.jsdelivr.net/npm/papaparse@5.4.1/+esm';

export function parseCSV(file) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: results => resolve(results.data.map(r => r.numero).filter(Boolean)),
      error: reject
    });
  });
}
