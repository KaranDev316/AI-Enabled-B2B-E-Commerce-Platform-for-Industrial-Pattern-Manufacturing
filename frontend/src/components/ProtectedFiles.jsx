import React, { useEffect, useState } from 'react';
import { fetchProtectedFile } from '../utils/protectedFiles.js';

export function ProtectedDownload({ href, children, className, style }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function download() {
    setBusy(true);
    setError('');
    try {
      const { blob, filename } = await fetchProtectedFile(href);
      const objectUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = objectUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      // Give the browser time to start saving before releasing the blob.
      setTimeout(() => URL.revokeObjectURL(objectUrl), 60000);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }
  return <>
    <button type="button" className={className} style={style} disabled={busy} onClick={download}>
      {busy ? 'Downloading…' : children}
    </button>
    {error && <span className="text-danger small" role="alert">{error}</span>}
  </>;
}

export function ProtectedPreview({ href, fileName, contentType, className = 'img-fluid rounded shadow-sm', style = { maxHeight: '70vh', objectFit: 'contain' } }) {
  const [file, setFile] = useState({ href: '', url: '', error: '' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    let objectUrl;
    setFile({ href, url: '', error: '' });
    fetchProtectedFile(href, { signal: controller.signal }).then(({ blob }) => {
      if (controller.signal.aborted) return;
      // Never render active HTML/SVG returned by an attachment endpoint.
      if (!['application/pdf', 'image/png', 'image/jpeg', 'image/webp', 'image/gif'].includes(blob.type)) {
        throw new Error('Preview is unavailable for this file type. Please download it.');
      }
      objectUrl = URL.createObjectURL(blob);
      setFile({ href, url: objectUrl, error: '' });
    }).catch(err => {
      if (!controller.signal.aborted) setFile({ href, url: '', error: err.message });
    });
    return () => {
      controller.abort();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [href, attempt]);
  if (file.href !== href || (!file.url && !file.error)) return <p role="status">Loading preview…</p>;
  if (file.error) return <div role="alert"><p>{file.error}</p><button type="button" className="btn btn-outline-secondary btn-sm" onClick={() => setAttempt(value => value + 1)}>Retry</button></div>;
  return contentType === 'application/pdf'
    ? <iframe src={file.url} title={fileName} style={{ width: '100%', height: '70vh', border: 'none', borderRadius: '8px' }} />
    : <img src={file.url} alt={fileName} className={className} style={style} />;
}
