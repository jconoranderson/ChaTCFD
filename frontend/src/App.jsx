import { useState } from 'react';
import ChatPanel from './components/ChatPanel.jsx';
import BipForm from './components/BipForm.jsx';

const tabs = [
  {
    id: 'general',
    label: 'General Assistant',
    description: 'Ask questions about policies, procedures, and internal resources.',
    endpoint: '/chat/general',
  },
  {
    id: 'benefits',
    label: 'Benefits Advisor',
    description: 'Get answers about provider options, coverage, and next steps.',
    endpoint: '/chat/benefits',
  },
  {
    id: 'bip',
    label: 'Behavior Plan Studio',
    description: 'Generate BIPs aligned with Center for Discovery standards.',
    endpoint: null,
  },
];

export default function App() {
  const [activeTab, setActiveTab] = useState('general');

  const activeDefinition = tabs.find(tab => tab.id === activeTab) ?? tabs[0];

  return (
    <div className="min-h-screen bg-gradient-to-br from-tcfd-cream via-white to-tcfd-cream">
      <header className="bg-white/80 backdrop-blur border-b border-slate-100">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-6 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.3em] text-tcfd-orange sm:text-base">#WhatHappensHereMattersEverywhere</p>
            <h1 className="text-4xl font-bold text-tcfd-navy sm:text-5xl">ChaTCFD</h1>
            <p className="text-base text-slate-500 sm:text-lg">Unified assistants for policies, benefits, and behavioural planning.</p>
          </div>
          <div className="flex items-center justify-end">
            <img
              src="/tcfd.jpg"
              alt="The Center for Discovery"
              className="h-16 w-auto rounded-lg shadow-card"
            />
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
        <nav className="flex flex-wrap gap-3">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-full border px-5 py-2 text-sm font-semibold transition ${
                activeTab === tab.id
                  ? 'border-tcfd-orange bg-tcfd-orange text-white shadow'
                  : 'border-slate-200 bg-white text-slate-600 hover:border-tcfd-orange/50 hover:text-tcfd-orange'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        <section className="min-h-[70vh] rounded-3xl border border-slate-100 bg-white/70 p-6 shadow-card backdrop-blur">
          {activeDefinition.id === 'bip' ? (
            <BipForm />
          ) : (
            <ChatPanel
              key={activeDefinition.id}
              mode={activeDefinition.id}
              title={activeDefinition.label}
              description={activeDefinition.description}
              endpoint={activeDefinition.endpoint}
            />
          )}
        </section>
      </main>
    </div>
  );
}
