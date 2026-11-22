import React, { useState } from 'react';
import { ProtectedDownload, ProtectedPreview } from './ProtectedFiles';

/** Fetch a private preview only when explicitly expanded, retaining per-tab auth. */
export function PrivateAttachment({href,fileName,contentType}) {
  const [open,setOpen]=useState(false);
  const previewable=['image/jpeg','image/png','application/pdf'].includes(contentType);
  return <div className="issue-file"><ProtectedDownload href={href} className="btn btn-sm btn-outline-secondary">Download {fileName}</ProtectedDownload>{previewable&&<details onToggle={event=>setOpen(event.currentTarget.open)}><summary>Preview {fileName}</summary>{open&&<ProtectedPreview href={`${href}?preview=true`} fileName={fileName} contentType={contentType}/>}</details>}</div>;
}
