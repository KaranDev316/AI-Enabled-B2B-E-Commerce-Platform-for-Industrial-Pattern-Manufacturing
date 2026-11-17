// A small text PDF with no external service or runtime dependency.
export function downloadSpecifications(title, rows) {
  const ascii = value => String(value).normalize('NFKD').replace(/[^\x20-\x7e]/g, ' ').replace(/([\\()])/g, '\\$1');
  const lines = ['KHODEL PATTERN CRAFT', title, 'Capability specification summary', '', ...rows.map(([label, value]) => `${label}: ${value}`), '', 'Final specifications, price and lead time require an official quotation.'];
  const wrapped = lines.flatMap(line => line.match(/.{1,78}(?:\s|$)|.{1,78}/g) || ['']);
  const stream = `BT /F1 11 Tf 45 790 Td 17 TL ${wrapped.map((line, i) => `${i ? 'T* ' : ''}(${ascii(line.trim())}) Tj`).join('\n')} ET`;
  const objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>', '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>', `<< /Length ${stream.length} >>\nstream\n${stream}\nendstream`];
  let pdf = '%PDF-1.4\n'; const offsets = [0];
  objects.forEach((obj,i) => { offsets.push(pdf.length); pdf += `${i+1} 0 obj\n${obj}\nendobj\n`; });
  const xref = pdf.length;
  pdf += `xref\n0 6\n0000000000 65535 f \n${offsets.slice(1).map(n => String(n).padStart(10,'0')+' 00000 n \n').join('')}trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  const url = URL.createObjectURL(new Blob([pdf], {type:'application/pdf'}));
  const link = document.createElement('a'); link.href = url; link.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g,'-')}-specifications.pdf`; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
