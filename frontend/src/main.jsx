import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Link, Route, Routes } from 'react-router-dom';
import 'bootstrap/dist/css/bootstrap.min.css';
import './styles.css';

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api';

function Workspace() {
  const [status, setStatus] = useState('Checking API connection…');

  useEffect(() => {
    const controller = new AbortController();
    async function checkConnection() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          credentials: 'same-origin',
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('API unavailable');
        const data = await response.json();
        if (data.status !== 'ok') throw new Error('Unexpected response');
        setStatus('API connected. Database and authentication setup are separate checks.');
      } catch (error) {
        if (error.name !== 'AbortError') {
          setStatus('API unavailable. Start the backend and refresh this page.');
        }
      }
    }
    checkConnection();
    return () => controller.abort();
  }, []);

  return (
    <main className="container py-5">
      <div className="workspace mx-auto p-4 p-md-5">
        <p className="brand mb-1">KPC</p>
        <p className="text-uppercase small">Khodel Pattern Craft</p>
        <h1 className="h2 mt-4">Development workspace</h1>
        <p className="text-secondary">Final-year BCA project · Project foundation</p>
        <p role="status" className="connection p-3 rounded">{status}</p>
        <p className="mb-0">The product screens and secure login will be implemented through the documented slices.</p>
      </div>
    </main>
  );
}

function NotFound() {
  return <main className="container py-5"><h1>Page not found</h1><Link to="/">Return to workspace</Link></main>;
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Workspace />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
);
