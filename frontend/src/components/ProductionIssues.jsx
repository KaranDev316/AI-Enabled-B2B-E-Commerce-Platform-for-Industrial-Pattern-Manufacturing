import React, { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { PrivateAttachment } from './PrivateAttachment';
import { emitKpcSync, useCrossTabSync } from '../utils/crossTabSync';
import '../pages/ProductionIssues.css';
const API=import.meta.env.VITE_API_BASE_URL||'/api';
const blank={job_id:'',issue_type:'production',title:'',description:'',priority:'medium'};
const label=value=>value.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
const time=value=>new Date(/Z$|[+-]\d\d:\d\d$/.test(value)?value:`${value}Z`).toLocaleString();
export function ProductionIssues({admin=false}) {
  const {csrfToken}=useAuth();
  const [issues,setIssues]=useState([]), [jobs,setJobs]=useState([]), [form,setForm]=useState(blank), [files,setFiles]=useState([]);
  const [selected,setSelected]=useState(null), [filter,setFilter]=useState(''), [loading,setLoading]=useState(true), [busy,setBusy]=useState(false);
  const [error,setError]=useState(''),[notice,setNotice]=useState(''),[handling,setHandling]=useState({status:'in_review',note:'',expected_version:0}),[fileKey,setFileKey]=useState(0);
  const issue=issues.find(i=>i.id===selected);
  async function request(path='',options={}) {
    const r=await fetch(`${API}/production/issues${path}`,{credentials:'same-origin',...options,headers:{...(options.body instanceof FormData?{}:options.body?{'Content-Type':'application/json'}:{}),...(options.method?{'X-CSRF-Token':csrfToken}:{})}});
    const b=await r.json().catch(()=>({}));
    if(!r.ok) throw Error(typeof b.detail==='string'?b.detail:b.detail?.message||`Request failed (${r.status}).`);
    return b;
  }
  async function refresh(){setIssues(await request());}
  useEffect(()=>{const c=new AbortController();setLoading(true);request('',{signal:c.signal}).then(setIssues).catch(e=>{if(!c.signal.aborted)setError(e.message);}).finally(()=>{if(!c.signal.aborted)setLoading(false);});
    if(!admin) fetch(`${API}/production/employee/jobs`,{signal:c.signal,credentials:'same-origin'}).then(async r=>{if(!r.ok) throw Error('Assigned jobs could not be loaded. You can still report an unlinked issue.');setJobs(await r.json());}).catch(e=>{if(!c.signal.aborted)setError(e.message);});
    return()=>c.abort();},[admin]);
  useCrossTabSync(refresh,5000);
  function clear(){setForm(blank);setFiles([]);setFileKey(v=>v+1);}
  async function submit(e){e.preventDefault();setError('');setNotice('');
    if(files.length>2||files.some(f=>f.size>20*1024*1024)){setError('Choose at most two files, up to 20 MB each.');return;}
    setBusy(true);try{const body=new FormData();Object.entries(form).forEach(([k,v])=>{if(v!=='')body.append(k,v);});files.forEach(f=>body.append('files',f));const saved=await request('',{method:'POST',body});setIssues(prev=>[saved,...prev.filter(i=>i.id!==saved.id)]);setSelected(saved.id);clear();setNotice('Issue reported. Admin can now review it.');emitKpcSync('PRODUCTION_ISSUE_UPDATED');}catch(e){setError(e.message);}finally{setBusy(false);}}
  async function saveHandling(e){e.preventDefault();if(!issue)return;setBusy(true);setError('');setNotice('');try{const saved=await request(`/${issue.id}`,{method:'PATCH',body:JSON.stringify({...handling,expected_version:handling.expected_version})});setIssues(prev=>prev.map(i=>i.id===saved.id?saved:i));setHandling({status:saved.status,note:'',expected_version:saved.version});setNotice('Handling update saved.');emitKpcSync('PRODUCTION_ISSUE_UPDATED');}catch(e){setError(e.message);}finally{setBusy(false);}}
  return <section className="production-issues">{error&&<div role="alert" className="alert alert-danger">{error} <button className="btn btn-sm btn-outline-danger" onClick={()=>refresh().then(()=>setError('')).catch(e=>setError(e.message))}>Refresh</button></div>}{notice&&<div role="status" className="alert alert-success">{notice}</div>}
    <div className={admin?'issue-admin-grid':'employee-issue-grid'}>
    {!admin&&<section className="card"><div className="customer-section-header"><h2>Raise a New Issue</h2></div><form className="issue-body" onSubmit={submit}><fieldset disabled={busy}>
      <div className="issue-fields"><label>Related Job (optional)<select className="form-select" value={form.job_id} onChange={e=>setForm({...form,job_id:e.target.value})}><option value="">No related job</option>{jobs.map(j=><option key={j.id} value={j.id}>Job #{j.id} · {j.order_number}</option>)}</select></label>
      <label>Issue Type<select className="form-select" value={form.issue_type} onChange={e=>setForm({...form,issue_type:e.target.value})}>{['production','machine','material','drawing'].map(t=><option key={t} value={t}>{label(t)} issue</option>)}</select></label></div>
      <label>Title<input className="form-control" required minLength={3} maxLength={200} value={form.title} onChange={e=>setForm({...form,title:e.target.value})}/></label>
      <label>Description<textarea className="form-control" required minLength={10} maxLength={10000} rows={5} value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label>
      <fieldset className="issue-priorities"><legend>Priority</legend>{[['high','Stops production'],['medium','Affects progress'],['low','Minor / non-blocking']].map(([p,note])=><label key={p} className={form.priority===p?'selected':''}><input type="radio" name="priority" value={p} checked={form.priority===p} onChange={()=>setForm({...form,priority:p})}/><span><strong>{label(p)}</strong><small>{note}</small></span></label>)}</fieldset>
      <label>Attach Files (optional)<input key={fileKey} type="file" className="form-control" multiple accept=".jpg,.jpeg,.png,.pdf" onChange={e=>setFiles(Array.from(e.target.files))}/><small>JPG, PNG or PDF · maximum 2 files, 20 MB each</small></label>
      {files.map((f,i)=><div key={`${f.name}-${i}`} className="issue-file">{f.name}<button type="button" className="btn btn-sm btn-outline-secondary" onClick={()=>{setFiles(files.filter((_,j)=>j!==i));setFileKey(v=>v+1);}}>Remove</button></div>)}
      <div className="issue-actions"><button type="button" className="btn btn-outline-secondary" onClick={clear}>Clear</button><button className="btn btn-primary" type="submit">{busy?'Submitting…':'Submit Issue'}</button></div>
    </fieldset></form></section>}
    <section className="card"><div className="customer-section-header"><h2>{admin?'Production Issues':'My Reported Issues'}</h2><select aria-label="Filter issues by status" className="form-select w-auto" value={filter} onChange={e=>setFilter(e.target.value)}><option value="">All Status</option>{['open','in_review','in_progress','resolved'].map(s=><option key={s} value={s}>{label(s)}</option>)}</select></div>
      <div className="issue-body">{loading&&<p role="status">Loading issues…</p>}{!loading&&!issues.filter(i=>!filter||i.status===filter).length&&<p>No reported issues match this status.</p>}
      {issues.filter(i=>!filter||i.status===filter).map(i=><button type="button" key={i.id} disabled={busy} className={`issue-row ${selected===i.id?'selected':''}`} onClick={()=>{setSelected(i.id);setHandling({status:i.status,note:'',expected_version:i.version});}}><span><strong>{i.title}</strong><small>#{i.id} · {label(i.issue_type)} · {label(i.priority)} priority{i.job_id?` · Job #${i.job_id}`:''}</small><time>{time(i.created_at)}</time></span><span className={`issue-status ${i.status}`}>{label(i.status)}</span></button>)}
      {issue&&<section className="issue-detail"><h3>{issue.title}</h3><p className="issue-description">{issue.description}</p><p>{admin?`Reported by Employee #${issue.employee_id} · `:''}{label(issue.priority)} priority · {label(issue.status)}</p>
      {issue.files.map(f=><PrivateAttachment key={f.id} href={`${API}${f.url.slice(4)}`} fileName={f.file_name} contentType={f.content_type}/>)}
      <h4>Handling History</h4>{issue.history.map(h=><article className="issue-event" key={h.id}><strong>{label(h.status)}</strong><time>{time(h.created_at)}</time><p>{h.note}</p></article>)}
      {admin&&<form onSubmit={saveHandling}><fieldset disabled={busy}><label>Handling Status<select className="form-select" value={handling.status} onChange={e=>setHandling({...handling,status:e.target.value})}>{['open','in_review','in_progress','resolved'].map(s=><option key={s} value={s}>{label(s)}</option>)}</select></label><label>Handling Note<textarea className="form-control" required minLength={3} maxLength={2000} value={handling.note} onChange={e=>setHandling({...handling,note:e.target.value})}/></label><button className="btn btn-primary" type="submit">{busy?'Saving…':'Save Handling Update'}</button></fieldset></form>}
      </section>}</div></section>
    </div></section>;
}
