import { useState } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

const initialForm = {
  name: '',
  age: '',
  diagnosis: '',
  behavior: '',
  setting: '',
  trigger: '',
  notes: '',
  model: '',
};

export default function BipForm() {
  const [form, setForm] = useState(initialForm);
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState('');

  const updateField = (key, value) => {
    setForm(current => ({ ...current, [key]: value }));
  };

  const handleSubmit = async event => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setResult('');

    const data = new FormData();
    Object.entries(form).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        data.append(key, value);
      }
    });
    if (file) {
      data.append('fba_file', file);
    }

    try {
      const response = await fetch(`${API_BASE_URL}/bip/generate`, {
        method: 'POST',
        body: data,
      });

      if (!response.ok) {
        const detail = await response.json().catch(() => ({}));
        throw new Error(detail.detail || 'Request failed');
      }

      const payload = await response.json();
      setResult(payload.bip ?? 'No plan was generated.');
    } catch (err) {
      console.error(err);
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid h-full grid-cols-1 gap-6 lg:grid-cols-5">
      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl bg-white p-6 shadow-card lg:col-span-2">
        <h2 className="text-2xl font-semibold text-tcfd-navy">BIP Generator</h2>
        <p className="text-sm text-slate-600">Upload an FBA and student details to generate a draft plan.</p>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium text-slate-700">Name</label>
            <input
              type="text"
              required
              value={form.name}
              onChange={event => updateField('name', event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Age</label>
            <input
              type="number"
              required
              value={form.age}
              onChange={event => updateField('age', event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
            />
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">Diagnosis</label>
          <input
            type="text"
            required
            value={form.diagnosis}
            onChange={event => updateField('diagnosis', event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">Target Behavior</label>
          <textarea
            required
            rows={2}
            value={form.behavior}
            onChange={event => updateField('behavior', event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
          />
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm font-medium text-slate-700">Setting</label>
            <input
              type="text"
              required
              value={form.setting}
              onChange={event => updateField('setting', event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-slate-700">Trigger</label>
            <input
              type="text"
              required
              value={form.trigger}
              onChange={event => updateField('trigger', event.target.value)}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
            />
          </div>
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">Notes (optional)</label>
          <textarea
            rows={3}
            value={form.notes}
            onChange={event => updateField('notes', event.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">Optional Model Override</label>
          <input
            type="text"
            value={form.model}
            onChange={event => updateField('model', event.target.value)}
            placeholder="e.g. llama3.1"
            className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-tcfd-sky focus:outline-none focus:ring-2 focus:ring-tcfd-sky/40"
          />
        </div>

        <div>
          <label className="text-sm font-medium text-slate-700">Upload FBA (PDF, DOCX, or TXT)</label>
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={event => setFile(event.target.files?.[0] ?? null)}
            className="mt-1 w-full text-sm"
          />
        </div>

        <button
          type="submit"
          className="w-full rounded-lg bg-tcfd-orange px-4 py-2 text-sm font-semibold text-white shadow hover:bg-orange-500 focus:outline-none focus:ring-2 focus:ring-orange-200 disabled:cursor-not-allowed disabled:bg-orange-300"
          disabled={loading}
        >
          {loading ? 'Generating…' : 'Generate BIP'}
        </button>

        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
            {error}
          </div>
        )}
      </form>

      <div className="min-h-[300px] rounded-2xl bg-white p-6 shadow-card lg:col-span-3">
        <h3 className="text-lg font-semibold text-tcfd-navy">Draft Plan</h3>
        <p className="text-sm text-slate-500">The generated plan appears below. Review and edit before sharing.</p>
        <div className="mt-4 h-full overflow-y-auto rounded-xl border border-slate-100 bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
          {result ? <pre className="whitespace-pre-wrap font-sans">{result}</pre> : 'Submit the form to generate a plan.'}
        </div>
      </div>
    </div>
  );
}
