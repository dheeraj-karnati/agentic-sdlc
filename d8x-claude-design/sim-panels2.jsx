// Per-agent artifact panels — D5 through D8
const { useState: useStateP2 } = React;
const { PanelHead: PH, Tag: TG } = window;
const {
  ArrowRight: AR2, Check: CK2, GitPullReq: GP2, Shield: SD2, Rocket: RK2, Layers: LY2,
  Activity: AC2, FileText: FT2, Code: CO2, Workflow: WF2, Gauge: GG2, Eye: EY2, Lock: LK2,
  ChevronDown: CD2, Plus: PL2, Alert: AL2
} = window.Icons;

// ───────────────────────────────────────────────── D5 PLAN ───
const D5_EPICS = [
  { id:'EP-1', title:'Auth + MFA', stories:8,  est:'21d', color:'flame' },
  { id:'EP-2', title:'KYC integration', stories:5, est:'13d' },
  { id:'EP-3', title:'Session management', stories:3, est:'5d' },
  { id:'EP-4', title:'Audit + telemetry', stories:2, est:'3d' },
];

const D5_STORIES = [
  { id:'AUTH-318', t:'Lock account after 5 failed attempts',     est:3, req:'req-2147', dep:[], status:'next' },
  { id:'AUTH-319', t:'Send MFA challenge on every login',         est:5, req:'req-2148', dep:['AUTH-318'] },
  { id:'AUTH-320', t:'Verify TOTP challenge in 30s window',       est:3, req:'req-2160', dep:['AUTH-319'] },
  { id:'AUTH-321', t:'Persist refresh tokens with 15min session', est:5, req:'req-2401', dep:['AUTH-320'] },
  { id:'KYC-104',  t:'Initiate KYC at signup; block activation',  est:5, req:'req-2210', dep:[] },
  { id:'KYC-105',  t:'Capture ID + selfie via provider SDK',      est:8, req:'req-2218', dep:['KYC-104'] },
  { id:'AUDIT-44', t:'Log all auth events to immutable store',    est:3, req:'req-2901', dep:[] },
];

function D5Panel() {
  return (
    <div>
      <PH tag="D5 · PLAN" name="Epics & sequenced stories"
        summary="Scope broken into epics, then into stories with acceptance criteria, estimates, and a dependency-aware order you can review before any code is written."
        stats={[{ value:'4', label:'epics' },{ value:'18', label:'stories' },{ value:'42d', label:'estimate' },{ value:'95%', label:'covered' }]} />
      <div className="p-7 space-y-5">
        {/* Epic cards */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {D5_EPICS.map(e => (
            <div key={e.id} className={`bg-ink-900 border ${e.color==='flame' ? 'border-flame/50' : 'hairline'} rounded-lg p-4`}>
              <div className="flex items-center justify-between">
                <span className="num text-[11px] text-ink-400">{e.id}</span>
                {e.color==='flame' && <TG tone="flame">Active</TG>}
              </div>
              <div className="mt-2 display text-[17px] font-semibold tracking-tight">{e.title}</div>
              <div className="mt-3 flex items-baseline justify-between text-[11.5px]">
                <span className="text-ink-300">{e.stories} stories</span>
                <span className="num text-ink-100">{e.est}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Story table */}
        <div className="bg-ink-900 border hairline rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-5 py-3 border-b hairline">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Dependency-ordered backlog · EP-1 Auth + MFA</div>
            <TG tone="ghost">Showing 7 of 18</TG>
          </div>
          <div className="divide-y hairline">
            {D5_STORIES.map((s,i) => (
              <div key={s.id} className="grid grid-cols-12 gap-3 items-center px-5 py-3.5 text-[13px] hover:bg-ink-850/50 transition">
                <span className="col-span-2 num text-[11px] text-flame">{s.id}</span>
                <span className="col-span-6 text-ink-100">{s.t}</span>
                <span className="col-span-1 num text-[11px] text-ink-400 text-right">{s.req}</span>
                <span className="col-span-2 text-[11px] text-ink-400 truncate">
                  {s.dep.length ? <>← {s.dep.join(', ')}</> : <span className="text-moss">no deps</span>}
                </span>
                <span className="col-span-1 num text-[12px] text-ink-100 text-right">{s.est} pt</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────── D6 BUILD ───
const D6_PRS = [
  { id:'#482', t:'auth: enforce MAX_RETRIES = 5 with lockout',  reqs:['req-2147'], files:7,  add:124, del:38, status:'open',   ci:'green' },
  { id:'#483', t:'mfa: mandatory TOTP gate at login',           reqs:['req-2148','req-2160'], files:11, add:312, del:14, status:'open',   ci:'green' },
  { id:'#484', t:'session: reduce TTL to 15min, sliding refresh', reqs:['req-2401'], files:4,  add:46,  del:62, status:'review', ci:'green' },
  { id:'#485', t:'kyc: block activation pending verification',  reqs:['req-2210'], files:9,  add:218, del:11, status:'review', ci:'green' },
  { id:'#486', t:'data: encrypt PII columns via KMS',           reqs:['req-3104'], files:6,  add:97,  del:24, status:'review', ci:'amber' },
  { id:'#487', t:'audit: append-only auth event log',           reqs:['req-2901'], files:5,  add:148, del:0,  status:'draft',  ci:'gray' },
];

function D6Panel() {
  return (
    <div>
      <PH tag="D6 · BUILD" name="Pull requests"
        summary="Feature branches and PRs against your repo. Each PR cites the requirement IDs it implements and the D2 conflicts it resolved — your reviewers see lineage, not just code."
        stats={[{ value:'12', label:'PRs opened' },{ value:'8', label:'in review' },{ value:'94%', label:'tests passing' }]} />
      <div className="p-7 grid lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 bg-ink-900 border hairline rounded-lg overflow-hidden">
          <div className="px-5 py-3 border-b hairline flex items-center justify-between">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Pull requests · acme-banking/api</div>
            <TG tone="ghost">main ← feature/*</TG>
          </div>
          <div className="divide-y hairline">
            {D6_PRS.map(p => (
              <div key={p.id} className="px-5 py-3.5 hover:bg-ink-850/40 transition">
                <div className="flex items-center gap-3">
                  <GP2 size={14} strokeWidth={1.8} className={`shrink-0 ${p.status==='open'?'text-flame':p.status==='review'?'text-ink-200':'text-ink-400'}`}/>
                  <span className="num text-[11px] text-ink-400">{p.id}</span>
                  <span className="text-[13.5px] text-ink-50 flex-1 truncate">{p.t}</span>
                  <span className="hidden sm:flex items-center gap-1">
                    {p.reqs.map(r=><TG key={r} tone="ghost">{r}</TG>)}
                  </span>
                  <span className="num text-[11px] text-moss">+{p.add}</span>
                  <span className="num text-[11px] text-flame">-{p.del}</span>
                  <CIDot kind={p.ci}/>
                </div>
              </div>
            ))}
          </div>
        </div>
        <div className="lg:col-span-5 bg-ink-900 border hairline rounded-lg overflow-hidden">
          <div className="px-4 py-2.5 border-b hairline flex items-center gap-2">
            <CO2 size={12} className="text-ink-300"/>
            <span className="num text-[11.5px] text-ink-200">auth_service.py</span>
            <TG tone="flame">#482</TG>
          </div>
          <pre className="text-[11.5px] num leading-relaxed overflow-x-auto"><code>
{`@@ -119,7 +119,9 @@ class AuthService:
-    MAX_RETRIES = 3
+    MAX_RETRIES = 5                          # CONF-047
+    LOCKOUT_DURATION = timedelta(minutes=15)
 
     async def login(self, creds: Credentials) -> Session:
+        if self.is_locked(creds.user_id):    # req-2147
+            raise AccountLocked()
         user = await self.repo.find(creds.email)`}
          </code></pre>
          <div className="px-4 py-3 border-t hairline flex items-center justify-between text-[11.5px]">
            <span className="text-ink-300">Resolves <span className="text-flame">CONF-047</span> · implements <span className="text-ink-100">req-2147</span></span>
            <span className="num text-moss">7 checks ✓</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function CIDot({ kind }) {
  const c = kind==='green' ? 'bg-moss' : kind==='amber' ? 'bg-flame' : 'bg-ink-500';
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${c}`}></span>;
}

// ───────────────────────────────────────────────── D7 TEST ───
const D7_CATS = [
  { name:'Unit',         pass:847,  fail:0,  total:847,  cov:94 },
  { name:'Integration',  pass:142,  fail:2,  total:144,  cov:88 },
  { name:'End-to-end',   pass:38,   fail:0,  total:38,   cov:76 },
  { name:'Security (SAST)', pass:1, fail:1,  total:2,   cov:100, alt:'1 high finding' },
  { name:'Accessibility', pass:24,  fail:3,  total:27,   cov:91, alt:'3 contrast violations' },
];

function D7Panel() {
  return (
    <div>
      <PH tag="D7 · TEST" name="Verification results"
        summary="Unit, integration, and end-to-end tests, plus SAST and accessibility scans. Findings post back to each PR before any human review."
        stats={[{ value:'1,058', label:'tests run' },{ value:'5', label:'findings' },{ value:'89%', label:'coverage' },{ value:'2m 14s', label:'runtime' }]} />
      <div className="p-7 grid lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 bg-ink-900 border hairline rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400 mb-4">Test categories</div>
          <div className="space-y-3.5">
            {D7_CATS.map(c => (
              <div key={c.name}>
                <div className="flex items-center justify-between text-[12.5px] mb-1.5">
                  <span className="text-ink-100">{c.name}</span>
                  <span className="num text-ink-300">{c.pass}/{c.total} · {c.cov}% cov</span>
                </div>
                <div className="h-2 bg-ink-800 rounded-full overflow-hidden">
                  <div className="h-full flex">
                    <div className="bg-moss" style={{ width: `${(c.pass/c.total)*100}%` }}/>
                    <div className="bg-flame" style={{ width: `${(c.fail/c.total)*100}%` }}/>
                  </div>
                </div>
                {c.alt && <div className="mt-1 text-[10.5px] num text-flame">⚠ {c.alt}</div>}
              </div>
            ))}
          </div>
        </div>
        <div className="lg:col-span-5 space-y-3">
          <div className="bg-ink-900 border hairline rounded-lg p-5">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400 mb-3">Findings to triage</div>
            <ul className="space-y-2.5 text-[12.5px]">
              <li className="flex items-start gap-2.5"><AL2 size={14} className="text-flame mt-0.5 shrink-0"/><div><div className="text-ink-100">SAST: weak randomness in token generator</div><div className="num text-[10.5px] text-ink-400 mt-0.5">auth_service.py:204 · high · CWE-330</div></div></li>
              <li className="flex items-start gap-2.5"><AL2 size={14} className="text-flame mt-0.5 shrink-0"/><div><div className="text-ink-100">a11y: button contrast 3.8:1 (needs 4.5:1)</div><div className="num text-[10.5px] text-ink-400 mt-0.5">LoginScreen → primaryButton</div></div></li>
              <li className="flex items-start gap-2.5"><AL2 size={14} className="text-flame mt-0.5 shrink-0"/><div><div className="text-ink-100">Integration: KYC mock timeout flake</div><div className="num text-[10.5px] text-ink-400 mt-0.5">kyc.spec.ts:88 · 1 of 12 retries</div></div></li>
            </ul>
          </div>
          <div className="bg-ink-900 border hairline rounded-lg p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Coverage trend</div>
              <span className="num text-[11px] text-moss">▲ 4.2%</span>
            </div>
            <CovChart/>
          </div>
        </div>
      </div>
    </div>
  );
}

function CovChart() {
  const pts = [62,68,71,73,72,78,82,84,87,89];
  const max=100, w=300, h=80;
  const stepX = w/(pts.length-1);
  const path = pts.map((p,i)=>`${i===0?'M':'L'} ${i*stepX} ${h - (p/max)*h}`).join(' ');
  const area = `${path} L ${w} ${h} L 0 ${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto">
      <defs>
        <linearGradient id="cov" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ff7a3a" stopOpacity="0.35"/>
          <stop offset="100%" stopColor="#ff7a3a" stopOpacity="0"/>
        </linearGradient>
      </defs>
      <path d={area} fill="url(#cov)"/>
      <path d={path} stroke="#ff7a3a" strokeWidth="1.6" fill="none"/>
      {pts.map((p,i)=>(<circle key={i} cx={i*stepX} cy={h-(p/max)*h} r="2" fill="#ff7a3a"/>))}
    </svg>
  );
}

// ───────────────────────────────────────────────── D8 SHIP ───
function D8Panel() {
  const envs = [
    { name:'dev',     status:'deployed', t:'12m ago', commit:'a7f2c19', v:'v2.4.1' },
    { name:'staging', status:'deployed', t:'8m ago',  commit:'a7f2c19', v:'v2.4.1' },
    { name:'prod',    status:'rolling',  t:'now',     commit:'a7f2c19', v:'v2.4.1', pct:35 },
  ];
  return (
    <div>
      <PH tag="D8 · SHIP" name="Rollout & telemetry"
        summary="Promoted through your environments with health gates. Production telemetry streams back into D2 so future requirements stay grounded in what actually happened."
        stats={[{ value:'3', label:'envs' },{ value:'35%', label:'prod rollout' },{ value:'0', label:'incidents' },{ value:'p99 142ms', label:'latency' }]} />
      <div className="p-7 grid lg:grid-cols-12 gap-5">
        <div className="lg:col-span-12 bg-ink-900 border hairline rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400 mb-4">Promotion track</div>
          <div className="grid grid-cols-3 gap-3 relative">
            {envs.map((e,i)=>(
              <div key={e.name} className={`relative rounded-lg p-4 border ${e.status==='rolling' ? 'border-flame/50 bg-flame/[0.04]' : 'hairline bg-ink-850/60'}`}>
                <div className="flex items-center justify-between">
                  <span className="num text-[10.5px] uppercase tracking-[0.18em] text-ink-400">{e.name}</span>
                  {e.status==='rolling' ? <TG tone="flame">Rolling</TG> : <TG tone="moss">Live</TG>}
                </div>
                <div className="mt-2 display text-[20px] font-semibold tracking-tight num text-ink-50">{e.v}</div>
                <div className="text-[11px] num text-ink-400 mt-0.5">{e.commit} · {e.t}</div>
                {e.pct != null && (
                  <div className="mt-3">
                    <div className="h-1.5 bg-ink-800 rounded overflow-hidden">
                      <div className="h-full bg-flame" style={{ width:`${e.pct}%` }}/>
                    </div>
                    <div className="num text-[10.5px] text-ink-300 mt-1.5 flex items-center justify-between">
                      <span>canary {e.pct}%</span><span>auto-advance in 6m</span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        <div className="lg:col-span-6 bg-ink-900 border hairline rounded-lg p-5">
          <div className="flex items-center justify-between mb-3">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Production telemetry · last 15 min</div>
            <TG tone="moss">healthy</TG>
          </div>
          <div className="grid grid-cols-3 gap-4 mb-4">
            {[['Login success','99.87%','moss'],['p99 latency','142ms','default'],['Error rate','0.02%','moss']].map(([l,v,c])=>(
              <div key={l}>
                <div className="text-[10px] uppercase tracking-[0.16em] text-ink-400">{l}</div>
                <div className={`num text-[20px] font-semibold ${c==='moss'?'text-moss':'text-ink-50'}`}>{v}</div>
              </div>
            ))}
          </div>
          <Sparklines/>
        </div>

        <div className="lg:col-span-6 bg-ink-900 border hairline rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400 mb-3">Loop back to D2</div>
          <p className="text-[13px] text-ink-200 leading-relaxed">
            Production traffic since launch now informs the next iteration's requirements. D2 has flagged <span className="text-flame">3 emergent patterns</span> worth a follow-up engagement.
          </p>
          <ul className="mt-4 space-y-2 text-[12.5px]">
            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-flame mt-1.5 shrink-0"/><span className="text-ink-100">12% of 2FA challenges expire before user enters code → consider extending window</span></li>
            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-flame mt-1.5 shrink-0"/><span className="text-ink-100">KYC dropoff at "selfie capture" is 4× spec assumption</span></li>
            <li className="flex items-start gap-2"><span className="w-1.5 h-1.5 rounded-full bg-flame mt-1.5 shrink-0"/><span className="text-ink-100">EU region login latency 2.3× US — consider edge auth</span></li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function Sparklines() {
  const series = [
    { c:'#7aaa7a', pts:[20,22,18,24,26,23,25,28,24,26,25,27,29,28,30] },
    { c:'#ff7a3a', pts:[14,16,15,18,17,16,15,17,16,15,16,17,16,15,14] },
    { c:'#bdbdc6', pts:[40,42,38,44,46,43,45,48,44,46,45,47,49,48,50] },
  ];
  const w=300,h=60;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-auto">
      {series.map((s,si)=> {
        const stepX = w/(s.pts.length-1);
        const path = s.pts.map((p,i)=>`${i===0?'M':'L'} ${i*stepX} ${h - (p/60)*h}`).join(' ');
        return <path key={si} d={path} stroke={s.c} strokeWidth="1.4" fill="none" opacity={si===0?1:0.7}/>;
      })}
    </svg>
  );
}

Object.assign(window, { D5Panel, D6Panel, D7Panel, D8Panel });
