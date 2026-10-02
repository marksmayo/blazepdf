#!/usr/bin/env python3
"""Benchmark readers and write raw JSON plus an interactive self-contained report."""
from __future__ import annotations
import argparse, csv, ctypes, html, json, math, os, platform, queue, random, statistics, subprocess, sys, threading, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; RESULTS=ROOT/'results'; WARMUPS=1; BUILD_TIMEOUT=900
def load(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def run(c,timeout=300): return subprocess.run(c,cwd=ROOT,text=True,encoding='utf-8',errors='replace',capture_output=True,timeout=timeout)
def rev(path):
 r=run(['git','-C',str(ROOT/path),'rev-parse','HEAD']); return r.stdout.strip() if r.returncode==0 else 'external binary'
def bucket(n): return 'XS <50 KB' if n<5e4 else 'S 50–250 KB' if n<2.5e5 else 'M 250 KB–1 MB' if n<1e6 else 'L 1–5 MB' if n<5e6 else 'XL ≥5 MB'
def stats(v):
 if not v:return {}
 mean=statistics.fmean(v); sd=statistics.stdev(v) if len(v)>1 else 0
 ordered=sorted(v)
 percentile=lambda fraction: ordered[max(0,math.ceil(fraction*len(ordered))-1)]
 return {'min_ms':round(min(v),3),'max_ms':round(max(v),3),'mean_ms':round(mean,3),'median_ms':round(statistics.median(v),3),'p10_ms':round(percentile(.10),3),'p90_ms':round(percentile(.90),3),'p95_ms':round(percentile(.95),3),'stdev_ms':round(sd,3),'cv_percent':round(100*sd/mean,2) if mean else 0}
def machine_specs():
 def ps_value(expression):
  try:
   result=run(['powershell','-NoProfile','-Command',expression],timeout=10)
   return result.stdout.strip() if result.returncode==0 else ''
  except (OSError,subprocess.TimeoutExpired):
   return ''
 cpu=ps_value('(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)') or platform.processor() or 'unknown'
 memory=ps_value('[math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 1)')
 gpu_names=ps_value('(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name)')
 cpu_mhz=ps_value('(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty CurrentClockSpeed)')
 cpu_load=ps_value('(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average)')
 gpus=', '.join(dict.fromkeys(line.strip() for line in gpu_names.splitlines() if line.strip()))
 return {
  'platform': platform.platform(),
  'os': f'{platform.system()} {platform.release()} ({platform.version()})',
  'cpu_model': cpu,
  'cpu_count': os.cpu_count(),
  'cpu_mhz': int(cpu_mhz) if cpu_mhz.isdigit() else None,
  'cpu_load_percent': float(cpu_load) if cpu_load else None,
  'memory_gb': float(memory) if memory else None,
  'gpu': gpus or 'unknown',
  'python': platform.python_version(),
  'build_profile': 'release',
 }
def exe(r):
 p=r.get('executable') or os.environ.get(r.get('executable_env',''), '')
 if not p: return None
 path=Path(p)
 return path if path.is_absolute() else ROOT/path
def command(r,pdf):
 a=r['adapter']
 if a=='pdf-inspector':
  p=ROOT/r['path']/'target/release/pdf2md.exe'; return ([str(p),str(pdf),*r.get('args',['--raw'])],None) if p.exists() else (None,'release binary missing')
 if a=='blazepdf':
  p=ROOT/'target/release/blazepdf.exe'; return ([str(p),*r.get('args',[]),str(pdf)],None) if p.exists() else (None,'release binary missing')
 if a=='blazepdf-render':
  p=ROOT/'target/release/blazepdf.exe'
  if not p.exists(): return None,'release binary missing'
  artifact=ROOT/'target'/'benchmark-artifacts'/f"{r['id']}-{pdf.stem}.ppm"
  artifact.parent.mkdir(parents=True,exist_ok=True)
  return ([str(p),'--render',str(pdf),str(artifact)],None)
 if a=='caly-core':
  p=ROOT/'benchmarks/adapters/CalyRunner/bin/Release/net10.0/CalyRunner.dll'; return (['dotnet',str(p),*r.get('args',[]),str(pdf)],None) if p.exists() else (None,'runner missing')
 if a=='sumatra-bench':
  p=exe(r); return ([str(p),'-console','-bench',str(pdf),'1'],None) if p and p.exists() else (None,'Sumatra executable not configured')
 if a=='sumatra-tool-text':
  p=exe(r)
  if not p or not p.exists(): return None,'Sumatra tool executable not configured'
  artifact=ROOT/'target'/'benchmark-artifacts'/f"{r['id']}-{pdf.stem}.txt"
  artifact.parent.mkdir(parents=True,exist_ok=True)
  return [str(p),'convert','-o',str(artifact),'-F','text',str(pdf),'1'],None
 if a=='sumatra-tool-pages':
  p=exe(r); return ([str(p),'pages',str(pdf),'1'],None) if p and p.exists() else (None,'Sumatra tool executable not configured')
 if a=='mutool-text':
  p=exe(r); return ([str(p),'draw','-q','-F','text',str(pdf),'1'],None) if p and p.exists() else (None,'MuPDF mutool executable not configured')
 if a=='mutool-text-full':
  p=exe(r); return ([str(p),'draw','-q','-F','text',str(pdf)],None) if p and p.exists() else (None,'MuPDF mutool executable not configured')
 if a=='mutool-info':
  p=exe(r); return ([str(p),'info',str(pdf)],None) if p and p.exists() else (None,'MuPDF mutool executable not configured')
 if a=='mutool-render':
  p=exe(r)
  if not p or not p.exists(): return None,'MuPDF mutool executable not configured'
  artifact=ROOT/'target'/'benchmark-artifacts'/f"{r['id']}-{pdf.stem}.png"
  artifact.parent.mkdir(parents=True,exist_ok=True)
  return [str(p),'draw','-q','-r','150','-o',str(artifact),str(pdf),'1'],None
 if a=='qpdf-npages':
  p=exe(r); return ([str(p),'--show-npages',str(pdf)],None) if p and p.exists() else (None,'qpdf executable not configured')
 if a=='window-ready':
  p=exe(r); return ([str(p),*r.get('args',[]),str(pdf)],None) if p and p.exists() else (None,'reader executable not configured')
 if a=='window-ready-signal':
  p=exe(r); return ([str(p),*r.get('args',[]),str(pdf)],None) if p and p.exists() else (None,'reader executable not configured')
 if a=='command' and r.get('command'): return ([x.format(pdf=str(pdf)) for x in r['command']],None)
 return None,'adapter not configured'
def document_window_title(title,pdf,expected_title=None,reader_title=None):
 # reader_title is for readers that never name the document in their window
 # title. It proves the reader's own window is up, not that the document
 # loaded, so any reader using it must declare a work label claiming only that.
 candidates=[pdf.stem,expected_title,reader_title]
 def compact(value):
  return ''.join(ch for ch in value.casefold() if not ch.isspace() and ch not in '\u200b\u200c\u200d\ufeff')
 normalized=compact(title)
 return any(value and compact(value) in normalized for value in candidates)
def is_new_document_window(pid,title,existing_pids,pdf,expected_title=None,reader_title=None,allow_foreign_pid=False):
 return (allow_foreign_pid or pid not in existing_pids) and document_window_title(title,pdf,expected_title,reader_title)
def process_ids():
 x=run(['tasklist','/FO','CSV','/NH'])
 return {int(row[1]) for row in csv.reader(x.stdout.splitlines()) if len(row)>1 and row[1].isdigit()}
def window_ready(c,pdf,expected_title=None,reader_title=None,require_process_alive=False):
 launch=list(c)
 for i,arg in enumerate(launch):
  if arg.startswith('--user-data-dir='):
   launch[i]=arg+f'-bench-{time.time_ns()}'
 existing=process_ids()
 allow_foreign_pid=any(arg.startswith('--user-data-dir=') for arg in launch)
 p=subprocess.Popen(launch,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); start=time.perf_counter_ns(); u=ctypes.windll.user32
 while (time.perf_counter_ns()-start)<30e9:
  got=[]; CB=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
  def check(hwnd,_):
   pid=ctypes.c_ulong();u.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
   if pid.value==p.pid and u.IsWindowVisible(hwnd):
    size=u.GetWindowTextLengthW(hwnd);title=ctypes.create_unicode_buffer(size+1);u.GetWindowTextW(hwnd,title,size+1)
    if is_new_document_window(pid.value,title.value,existing,pdf,expected_title,reader_title,allow_foreign_pid):got.append(pid.value)
   return True
  u.EnumWindows(CB(check),0)
  if got:
   if require_process_alive and p.poll() is not None:
    continue
   ms=(time.perf_counter_ns()-start)/1e6
   for pid in set(got):run(['taskkill','/PID',str(pid),'/T','/F'],timeout=10)
   if p.poll() is None:p.terminate()
   return ms,None
  time.sleep(.02)
 if p.poll() is None:p.terminate()
 return None,'no visible document window within 30 seconds'
def visible_window_for_pid(pid):
 u=ctypes.windll.user32; found=[]; CB=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
 def check(hwnd,_):
  owner=ctypes.c_ulong();u.GetWindowThreadProcessId(hwnd,ctypes.byref(owner))
  if owner.value==pid and u.IsWindowVisible(hwnd): found.append(hwnd)
  return True
 u.EnumWindows(CB(check),0)
 return bool(found)
def window_ready_signal(c,marker='BLAZEPDF_FIRST_FRAME_READY',environment=None,require_visible_window=False,stable_window_ms=0):
 env=os.environ.copy();env.update(environment or {})
 p=subprocess.Popen(c,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,env=env,text=True,encoding='utf-8',errors='replace',bufsize=1)
 lines=queue.Queue()
 def read_lines():
  if p.stdout:
   for line in p.stdout: lines.put(line.rstrip())
 threading.Thread(target=read_lines,daemon=True).start()
 start=time.perf_counter_ns()
 try:
  while (time.perf_counter_ns()-start)<30e9:
   try:
    if lines.get(timeout=.02)==marker:
     ms=(time.perf_counter_ns()-start)/1e6
     if require_visible_window:
      stable_until=time.perf_counter_ns()+int(stable_window_ms*1e6)
      while time.perf_counter_ns()<stable_until:
       if p.poll() is not None or not visible_window_for_pid(p.pid): return None,'ready signal arrived without a stable visible window'
       time.sleep(.005)
      if not visible_window_for_pid(p.pid): return None,'ready signal arrived without a visible window'
     if p.poll() is None:p.terminate()
     return ms,None
   except queue.Empty:
    if p.poll() is not None: break
 finally:
  if p.poll() is None:p.terminate()
 return None,'ready signal not received within 30 seconds'
def measure(r,pdf,repeats,expected_title=None):
 c,why=command(r,pdf)
 if why:return {'status':'skipped','reason':why}
 samples=[];operation=[];out=''
 for _ in range(WARMUPS+repeats):
  try:
   if r['adapter']=='window-ready': ms,error=window_ready(c,pdf,expected_title,r.get('window_title'),r.get('require_process_alive',False)); 
   elif r['adapter']=='window-ready-signal': ms,error=window_ready_signal(c,r.get('ready_signal','BLAZEPDF_FIRST_FRAME_READY'),r.get('environment'),r.get('require_visible_window',False),r.get('stable_window_ms',0));
   else:
    t=time.perf_counter_ns();x=run(c);ms=(time.perf_counter_ns()-t)/1e6;error=None;out=((x.stdout or '')+(x.stderr or ''))[-2000:]
    if x.returncode:error=f'exit {x.returncode}'
    if not error and r['adapter']=='caly-core':operation.append(float(json.loads(x.stdout)['elapsed_ms']))
   if error:return {'status':'failed','reason':error,'command':c,'output':out}
  except (OSError,ValueError,KeyError,json.JSONDecodeError,subprocess.TimeoutExpired) as e:return {'status':'failed','reason':str(e),'command':c,'output':out}
  samples.append(round(ms,3))
 samples=samples[WARMUPS:]
 if len(samples)>=3 and max(samples)>statistics.median(samples)*1.5:
  # Keep the retry instead of replacing the outlier: the distribution stays
  # auditable while a transient scheduler stall gets one independent check.
  try:
   if r['adapter']=='window-ready-signal': ms,error=window_ready_signal(c,r.get('ready_signal','BLAZEPDF_FIRST_FRAME_READY'),r.get('environment'),r.get('require_visible_window',False),r.get('stable_window_ms',0))
   elif r['adapter']=='window-ready': ms,error=window_ready(c,pdf,expected_title,r.get('window_title'),r.get('require_process_alive',False))
   else:
    t=time.perf_counter_ns();x=run(c);ms=(time.perf_counter_ns()-t)/1e6;error=None
    if x.returncode:error=f'exit {x.returncode}'
   if not error:samples.append(round(ms,3))
  except (OSError,subprocess.TimeoutExpired): pass
 result={'status':'ok','command':c,'samples_ms':samples,'output':out,'launch_state':'cold process; warm OS cache after one excluded warm-up' if r['adapter'].startswith('window-ready') else None,**stats(samples)}
 if operation: result['operation']=stats(operation[WARMUPS:])
 return result
def report(data):
 payload=json.dumps(data,separators=(',',':')).replace('<','\\u003c'); sources=''.join(f'<li><a href="{html.escape(x["repository"])}">{html.escape(x["name"])}</a> <code>{html.escape(x["revision"][:12])}</code></li>' for x in data['readers'])
 machine=data.get('machine',{})
 machine_html=''.join(f'<div><b>{html.escape(label)}</b><span>{html.escape(str(machine.get(key) or "unknown"))}</span></div>' for key,label in [('os','OS'),('cpu_model','CPU'),('cpu_count','Logical CPUs'),('memory_gb','RAM (GB)'),('gpu','GPU'),('python','Python'),('build_profile','Build')])
 return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>BlazePDF benchmark</title><style>:root{{--ink:#11253f;--muted:#64748b;--paper:#f5f7fb;--line:#dce4f0;--blue:#2268d7;--teal:#079b86}}*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:14px system-ui,sans-serif}}header{{padding:50px max(24px,calc((100% - 1180px)/2));background:radial-gradient(circle at 90% 0,#337cec,#122b50 48%,#0c1c31);color:#fff}}h1{{font-size:40px;margin:0;letter-spacing:-1.5px}}h2{{font-size:18px;margin:30px 0 12px}}main{{max-width:1180px;margin:auto;padding:26px 24px 60px}}.eyebrow{{color:#9dc7ff;text-transform:uppercase;letter-spacing:1.4px;font-size:11px;font-weight:bold}}.sub,.hint{{color:var(--muted)}}header .sub{{color:#cad8eb}}.note{{background:#eaf1ff;border-left:4px solid var(--blue);padding:14px 16px;border-radius:6px;color:#38516e}}.machine{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px;margin:16px 0}}.machine h2{{margin:0 0 12px}}.machine-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.machine-grid div{{background:#f5f7fb;border-radius:8px;padding:10px}}.machine-grid b,.machine-grid span{{display:block}}.machine-grid b{{font-size:11px;color:var(--muted);text-transform:uppercase}}.machine-grid span{{margin-top:3px;word-break:break-word}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:20px 0}}.card,.chart,.controls,.table{{background:#fff;border:1px solid var(--line);border-radius:12px}}.card{{padding:16px;box-shadow:0 8px 25px #273b5e12}}.card b{{display:block;font-size:26px;letter-spacing:-1px;margin:4px 0}}.controls{{padding:15px;display:flex;gap:12px;flex-wrap:wrap}}label{{display:grid;gap:6px;color:#52657e;font-size:12px;font-weight:bold}}select{{padding:8px;border:1px solid var(--line);border-radius:7px;background:white;color:var(--ink)}}.chart{{padding:16px;margin-top:16px}}.head{{display:flex;justify-content:space-between;gap:15px;align-items:baseline}}svg{{width:100%;height:310px}}.grid{{stroke:#e5eaf2}}.axis,.label{{fill:#64748b;font-size:11px}}.bar{{fill:var(--blue)}}.dot{{fill:var(--teal);stroke:white;stroke-width:2}}.table{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}th{{position:sticky;top:0;background:#f2f6fb;color:#53667f;text-align:left;font-size:11px;text-transform:uppercase}}td,th{{padding:10px 12px;border-bottom:1px solid #e9edf3;white-space:nowrap}}td:nth-child(1),td:nth-child(2){{white-space:normal}}.num{{text-align:right;font-variant-numeric:tabular-nums}}.ok{{color:#078769;font-weight:bold}}.failed{{color:#bd4050;font-weight:bold}}.skipped{{color:#9a681e;font-weight:bold}}.tip{{position:fixed;background:#12243d;color:white;padding:8px;border-radius:6px;opacity:0;pointer-events:none;font-size:12px}}footer{{display:grid;grid-template-columns:1fr 1fr;gap:30px;color:var(--muted)}}@media(max-width:720px){{header{{padding:32px 22px}}h1{{font-size:30px}}main{{padding:20px 14px}}.cards{{grid-template-columns:repeat(2,1fr)}}.machine-grid{{grid-template-columns:repeat(2,1fr)}}footer{{grid-template-columns:1fr}}}}</style><header><div class="eyebrow">Performance lab / reproducible run</div><h1>BlazePDF benchmark</h1><p class="sub">{html.escape(data['generated_at'])} · {html.escape(data['machine'].get('platform','unknown'))}</p></header><main><div class="note">One warm-up is excluded; every score is based on {data['repeats']} measured runs. Compare results only within the same work label—reader readiness, rendering, and extraction are intentionally not collapsed into a false league table.</div><section class="machine"><h2>Test machine</h2><div class="machine-grid">{machine_html}</div></section><div class="cards" id="cards"></div><div class="controls"><label>Reader<select id="reader"><option value="all">All successful readers</option></select></label><label>File size<select id="size"><option value="all">All file sizes</option></select></label><label>Metric<select id="metric"><option value="median_ms">Median latency</option><option value="mean_ms">Mean latency</option><option value="p95_ms">p95 latency</option><option value="stdev_ms">Standard deviation</option><option value="throughput_mbps">Throughput</option></select></label></div><section class="chart"><div class="head"><h2 id="barhead">Reader comparison</h2><span class="hint" id="barnote"></span></div><svg id="bars"></svg></section><section class="chart"><div class="head"><h2>Latency by input size</h2><span class="hint">document medians; logarithmic size axis</span></div><svg id="scatter"></svg></section><h2>Per-document evidence</h2><div class="table"><table><thead><tr><th>Reader</th><th>Work</th><th>Document</th><th>Size</th><th>Status</th><th class="num">Min</th><th class="num">Mean</th><th class="num">Median</th><th class="num">p95</th><th class="num">Max</th><th class="num">σ</th><th class="num">CV</th><th class="num">MB/s</th></tr></thead><tbody id="rows"></tbody></table></div><footer><div><h2>Method</h2><p>Adapters use their native supported paths: classification/extraction, open + first-page text layer, full-page rendering, or time to a visible document window. The report preserves per-run samples and command output in raw JSON.</p></div><div><h2>Sources</h2><ul>{sources}</ul><p>Raw data: <code>{html.escape(data['raw_file'])}</code></p></div></footer></main><div id="tip" class="tip"></div><script>const data={payload},R=data.measurements,$=x=>document.getElementById(x),fm=n=>n==null?'—':n>=1000?(n/1000).toFixed(2)+' s':n.toFixed(2)+' ms',fb=n=>n<1e6?(n/1e3).toFixed(0)+' KB':(n/1e6).toFixed(2)+' MB';[...new Set(R.map(x=>x.reader))].forEach(x=>$('reader').innerHTML+=`<option>${{x}}</option>`);[...new Set(R.map(x=>x.size_bucket))].forEach(x=>$('size').innerHTML+=`<option>${{x}}</option>`);function get(){{return R.filter(x=>x.status==='ok'&&($('reader').value==='all'||x.reader===$('reader').value)&&($('size').value==='all'||x.size_bucket===$('size').value))}}function val(x,m){{return m==='throughput_mbps'?x.bytes/(x.median_ms/1000)/1e6:x[m]}}function chart(items,m){{let g={{}};items.forEach(x=>(g[x.reader]??=[]).push(val(x,m)));let a=Object.entries(g).map(([n,v])=>[n,v.reduce((x,y)=>x+y)/v.length]).sort((x,y)=>x[1]-y[1]),s=$('bars'),w=s.clientWidth,h=310,L=160,max=Math.max(1,...a.map(x=>x[1]));s.setAttribute('viewBox',`0 0 ${{w}} ${{h}}`);let z='';for(let i=0;i<5;i++){{let x=L+(w-L-25)*i/4;z+=`<line class="grid" x1="${{x}}" y1="20" x2="${{x}}" y2="275"/><text class="axis" x="${{x}}" y="299" text-anchor="middle">${{m==='throughput_mbps'?(max*i/4).toFixed(2)+' MB/s':fm(max*i/4)}}</text>`}}a.forEach(([n,v],i)=>{{let y=25+i*250/Math.max(a.length,1),bh=Math.max(15,250/Math.max(a.length,1)-10);z+=`<text class="label" x="${{L-8}}" y="${{y+bh/2+4}}" text-anchor="end">${{n}}</text><rect class="bar" x="${{L}}" y="${{y}}" width="${{(w-L-25)*v/max}}" height="${{bh}}" rx="4"><title>${{n}}: ${{fm(v)}}</title></rect>`}});s.innerHTML=z;$('barhead').textContent=(m==='throughput_mbps'?'Mean throughput':'Mean '+m.replace('_ms','').replace('_',' '))+' by reader';$('barnote').textContent=a.length+' comparable work groups'}}function scatter(items){{let s=$('scatter'),w=s.clientWidth,h=310,L=62,b=35,logs=items.map(x=>Math.log10(x.bytes)),lo=Math.min(...logs),hi=Math.max(...logs),mx=Math.max(1,...items.map(x=>x.median_ms));s.setAttribute('viewBox',`0 0 ${{w}} ${{h}}`);let z='';for(let i=0;i<5;i++){{let x=L+(w-L-25)*i/4,y=h-b-(h-b-20)*i/4;z+=`<line class="grid" x1="${{x}}" y1="20" x2="${{x}}" y2="${{h-b}}"/><line class="grid" x1="${{L}}" y1="${{y}}" x2="${{w-25}}" y2="${{y}}"/><text class="axis" x="${{x}}" y="${{h-10}}" text-anchor="middle">${{fb(10**(lo+(hi-lo)*i/4))}}</text><text class="axis" x="${{L-7}}" y="${{y+4}}" text-anchor="end">${{fm(mx*i/4)}}</text>`}}items.forEach(x=>{{let cx=L+(w-L-25)*(Math.log10(x.bytes)-lo)/(hi-lo||1),cy=h-b-(h-b-20)*x.median_ms/mx;z+=`<circle class="dot" cx="${{cx}}" cy="${{cy}}" r="5"><title>${{x.reader}} · ${{x.document}} · ${{fm(x.median_ms)}}</title></circle>`}});s.innerHTML=z}}function render(){{let I=get(),m=$('metric').value,all=I.flatMap(x=>x.samples_ms),mean=all.reduce((a,b)=>a+b,0)/(all.length||1);$('cards').innerHTML=`<div class="card"><span class="hint">Successful cases</span><b>${{I.length}}</b><span class="hint">of ${{R.length}} entries</span></div><div class="card"><span class="hint">Measured runs</span><b>${{all.length}}</b><span class="hint">warm-ups excluded</span></div><div class="card"><span class="hint">Mean sampled latency</span><b>${{fm(mean)}}</b><span class="hint">selected scope</span></div><div class="card"><span class="hint">Input range</span><b>${{I.length?fb(Math.min(...I.map(x=>x.bytes)))+'–'+fb(Math.max(...I.map(x=>x.bytes))):'—'}}</b><span class="hint">fixture bytes</span></div>`;chart(I,m);scatter(I);$('rows').innerHTML=R.filter(x=>($('reader').value==='all'||x.reader===$('reader').value)&&($('size').value==='all'||x.size_bucket===$('size').value)).map(x=>`<tr><td>${{x.reader}}</td><td>${{x.work}}</td><td>${{x.document}}</td><td>${{fb(x.bytes)}}<br><span class="hint">${{x.size_bucket}}</span></td><td class="${{x.status}}">${{x.status}}</td><td class="num">${{fm(x.min_ms)}}</td><td class="num">${{fm(x.mean_ms)}}</td><td class="num">${{fm(x.median_ms)}}</td><td class="num">${{fm(x.p95_ms)}}</td><td class="num">${{fm(x.max_ms)}}</td><td class="num">${{fm(x.stdev_ms)}}</td><td class="num">${{x.cv_percent==null?'—':x.cv_percent+'%'}}</td><td class="num">${{x.status==='ok'?(x.bytes/(x.median_ms/1000)/1e6).toFixed(2):'—'}}</td></tr>`).join('')}}['reader','size','metric'].forEach(x=>$(x).onchange=render);new ResizeObserver(render).observe($('bars'));render()</script>'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--repeats',type=int,default=5);p.add_argument('--reader',action='append');p.add_argument('--seed',type=int,default=20260925);p.add_argument('--no-canonical',action='store_true');a=p.parse_args();readers=load('benchmarks/readers.json')['readers'];docs=load('benchmarks/corpus.json')['documents'];readers=[r for r in readers if not a.reader or r['id'] in a.reader]
 built_commands=set()
 for r in readers:
  if r.get('build'):
   build_key=tuple(r['build'])
   if build_key in built_commands:
    r['build_error']=None
    continue
   print('Building '+r['name']+'…',flush=True)
   try:
    x=run(r['build'],timeout=BUILD_TIMEOUT)
    r['build_error']=((x.stdout or '')+(x.stderr or ''))[-2000:] if x.returncode else None
   except subprocess.TimeoutExpired:
    r['build_error']=f'build timed out after {BUILD_TIMEOUT} seconds'
   built_commands.add(build_key)
 entries=[]; jobs=[(r,d) for r in readers for d in docs]; random.Random(a.seed).shuffle(jobs)
 for r,d in jobs:
   pdf=ROOT/d['path'];e={'reader':r.get('product',r['name']),'adapter_name':r['name'],'product':r.get('product',r['name']),'reader_id':r['id'],'work':r['work'],'document':d['label'],'document_id':d['id'],'tags':d['tags'],'bytes':pdf.stat().st_size if pdf.exists() else 0};e['size_bucket']=bucket(e['bytes']);e.update({'status':'skipped','reason':'fixture missing'} if not pdf.exists() else {'status':'failed','reason':'build failed','output':r['build_error']} if r.get('build_error') else measure(r,pdf,a.repeats,d.get('window_title')));entries.append(e);print(f"{r['name']}: {d['label']}: {e['status']}",flush=True)
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ');RESULTS.mkdir(exist_ok=True);raw=f'benchmark-{stamp}.json';data={'generated_at':datetime.now(timezone.utc).isoformat(),'raw_file':raw,'repeats':a.repeats,'warmups_excluded':WARMUPS,'machine':machine_specs(),'execution':{'randomization_seed':a.seed,'sample_policy':'one warm-up excluded; one additional sample is retained when a measured sample exceeds 1.5× the median','launch_validation':'signal adapters require a stable visible top-level window when configured'},'readers':[{'name':r.get('product',r['name']),'adapter_name':r['name'],'product':r.get('product',r['name']),'repository':r['repository'],'revision':rev(r['path']),'adapter':r['adapter'],'work':r['work']} for r in readers],'catalog':load('benchmarks/products.json')['products'],'measurements':entries};(RESULTS/raw).write_text(json.dumps(data,indent=2),encoding='utf-8');out=RESULTS/f'benchmark-{stamp}.html';out.write_text(report(data),encoding='utf-8');print(out)
 if not a.no_canonical:
  canonical=run([sys.executable,str(ROOT/'scripts'/'update_canonical_reports.py')])
  if canonical.returncode: print('Could not refresh canonical reports: '+canonical.stderr,flush=True)
  else: print(canonical.stdout.strip(),flush=True)
if __name__=='__main__':main()
