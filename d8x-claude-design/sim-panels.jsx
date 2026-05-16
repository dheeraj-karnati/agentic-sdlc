// Per-agent artifact panels — D1 through D4
const { useState: useStateP, useEffect: useEffectP, useMemo: useMemoP } = React;
const {
  ArrowRight: AR, ChevronRight: CR, ChevronDown: CD, Check: CK, X: XI, Plus: PL, Minus: MN, Alert: AL,
  FileText: FT, Mic: MC, Code: CO, Image: IM, Video: VD, Search: SR, Shapes: SH, Zap: ZP, Server: SV,
  Boxes: BX, GitPullReq: GP, Shield: SD, Rocket: RK, Lock: LK, Eye: EY, Building: BD, Users: US,
  Layers: LY, Activity: AC, Globe: GL, ArrowUpRight: AU, Workflow: WF, Gauge: GG, Terminal: TM, Sliders: SL
} = window.Icons;

// ── Shared bits ──
function PanelHead({ tag, name, summary, stats }) {
  return (
    <div className="px-7 pt-7 pb-5 border-b hairline">
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2.5">
            <span className="num text-[11px] uppercase tracking-[0.18em] text-flame">{tag}</span>
            <span className="w-6 h-px bg-flame/40"/>
            <span className="text-[11px] uppercase tracking-[0.18em] text-ink-400">artifact</span>
          </div>
          <h1 className="display mt-2 text-[28px] font-semibold tracking-tight text-ink-50 leading-tight">{name}</h1>
          <p className="mt-1.5 text-[14px] text-ink-300 max-w-[62ch] leading-relaxed">{summary}</p>
        </div>
        {stats && (
          <div className="hidden md:flex gap-px bg-white/5 border hairline rounded overflow-hidden shrink-0">
            {stats.map(s => (
              <div key={s.label} className="bg-ink-900 px-4 py-2.5">
                <div className="num text-[20px] font-semibold leading-none text-ink-50">{s.value}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.16em] text-ink-400">{s.label}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Tag({ children, tone="default" }) {
  const t = {
    default: 'text-ink-300 bg-ink-800 border hairline',
    flame:   'text-flame bg-flame/10 border border-flame/30',
    moss:    'text-moss bg-moss/10 border border-moss/30',
    ghost:   'text-ink-400 border hairline',
  }[tone] || 'text-ink-300';
  return <span className={`text-[10.5px] num uppercase tracking-[0.18em] px-1.5 py-0.5 rounded ${t}`}>{children}</span>;
}

// ───────────────────────────────────────────────── D1 INGEST ───
const D1_SOURCES = [
  { kind:'BRD',         name:'BRD_v3.pdf',                 size:'2.4 MB',  parsed:'847 paragraphs · 12 tables', icon: FT, time:'4.2s' },
  { kind:'SPEC',        name:'data_security_v2.md',        size:'48 KB',   parsed:'214 sections',               icon: FT, time:'0.8s' },
  { kind:'POLICY',      name:'privacy_policy.md',          size:'31 KB',   parsed:'68 clauses',                 icon: FT, time:'0.6s' },
  { kind:'REPO',        name:'acme-banking/api',           size:'847 files', parsed:'124k LOC · 312 endpoints', icon: CO, time:'18.4s' },
  { kind:'REPO',        name:'acme-banking/mobile',        size:'612 files', parsed:'81k LOC · React Native',   icon: CO, time:'12.1s' },
  { kind:'AUDIO',       name:'kickoff_2026-04-02.m4a',     size:'48 min',  parsed:'transcript + speakers',      icon: MC, time:'22.0s' },
  { kind:'AUDIO',       name:'arch_review_2026-04-09.m4a', size:'62 min',  parsed:'transcript + speakers',      icon: MC, time:'28.7s' },
  { kind:'CONFLUENCE',  name:'ACME / Mobile uplift',       size:'42 pages',parsed:'pages + attachments',        icon: BD, time:'9.3s' },
  { kind:'JIRA',        name:'AUTH project',               size:'318 issues', parsed:'epics, stories, history', icon: WF, time:'6.5s' },
  { kind:'FIGMA',       name:'Auth flows v2.4',            size:'37 frames', parsed:'components + comments',    icon: IM, time:'4.8s' },
  { kind:'LOOM',        name:'CTO walkthrough',            size:'14 min',  parsed:'transcript + slides',        icon: VD, time:'7.1s' },
  { kind:'SHAREPOINT',  name:'Compliance / KYC',           size:'18 docs', parsed:'PDFs + DOCX',                icon: BD, time:'11.0s' },
];

function D1Panel() {
  return (
    <div>
      <PanelHead tag="D1 · INGEST" name="Sources normalized"
        summary="Every artifact from the engagement has been parsed into structured documents with line-level provenance. Audio is transcribed with speaker diarization; codebases are indexed at the file and symbol level."
        stats={[
          { value:'12', label:'sources' },
          { value:'8,243', label:'entities' },
          { value:'2m 04s', label:'total parse' },
        ]} />
      <div className="p-7">
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {D1_SOURCES.map(s => {
            const I = s.icon;
            return (
              <div key={s.name} className="bg-ink-850 border hairline rounded-lg p-4 hover:border-white/15 transition group">
                <div className="flex items-start justify-between gap-3">
                  <div className="w-9 h-9 rounded bg-ink-800 border hairline-strong flex items-center justify-center text-ink-100 shrink-0">
                    <I size={16} strokeWidth={1.7}/>
                  </div>
                  <Tag tone="ghost">{s.kind}</Tag>
                </div>
                <div className="mt-3 text-[13.5px] font-medium text-ink-50 truncate">{s.name}</div>
                <div className="mt-0.5 text-[11.5px] num text-ink-400">{s.size}</div>
                <div className="mt-3 pt-3 border-t hairline flex items-center justify-between text-[11px]">
                  <span className="text-ink-300 truncate pr-2">{s.parsed}</span>
                  <span className="num text-moss shrink-0">✓ {s.time}</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-6 grid sm:grid-cols-2 gap-3">
          <div className="bg-ink-900 border hairline rounded-lg p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Entity types extracted</div>
            <div className="mt-3 grid grid-cols-4 gap-2 text-center">
              {[['Requirements','1,243'],['Rules','847'],['Entities','412'],['Actors','86']].map(([l,v]) => (
                <div key={l} className="bg-ink-850 rounded p-2.5">
                  <div className="num text-[18px] font-semibold text-ink-50">{v}</div>
                  <div className="text-[10px] text-ink-400 uppercase tracking-wider">{l}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-ink-900 border hairline rounded-lg p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Parse anomalies</div>
            <ul className="mt-3 space-y-1.5 text-[12.5px] text-ink-200">
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-flame"></span> 2 PDFs contain scanned pages (OCR applied)</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-flame"></span> Kickoff recording: 6 speakers identified, 1 unattributed</li>
              <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 rounded-full bg-moss"></span> All other sources parsed cleanly</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────── D2 DISCOVER ───
const D2_CONFLICTS = [
  { id:'CONF-047', sev:'high', title:'Retry policy disagreement',
    sources:[{k:'BRD',v:'3',c:true},{k:'CODE',v:'5'},{k:'NOTES',v:'5'}],
    line:'BRD_v3.pdf §4.2 vs. auth_service.py:122 vs. kickoff 23:14',
    rec:'Adopt 5; amend BRD §4.2.', conf:94 },
  { id:'CONF-051', sev:'critical', title:'PII encryption contradiction',
    sources:[{k:'SPEC',v:'enc',c:true},{k:'NOTES',v:'plain',c:true},{k:'CODE',v:'plain',c:true}],
    line:'data_security_v2 §3.1 vs. arch_review 41:02 vs. events.ts:88',
    rec:'Block v1; spec amendment with DPO sign-off required.', conf:99 },
  { id:'CONF-063', sev:'medium', title:'Retention window mismatch',
    sources:[{k:'POLICY',v:'90d',c:true},{k:'CODE',v:'365d',c:true}],
    line:'privacy_policy §7 vs. 2026_04_001.sql:14',
    rec:'Align TTL to policy or amend policy.', conf:88 },
  { id:'CONF-068', sev:'high', title:'KYC requirement vs. happy path',
    sources:[{k:'COMPLIANCE',v:'required',c:true},{k:'FIGMA',v:'skipped'}],
    line:'Compliance / KYC §2.1 vs. Auth flows v2.4 frame "express signup"',
    rec:'Add KYC step before account activation in mobile flow.', conf:91 },
  { id:'CONF-072', sev:'medium', title:'Session timeout drift',
    sources:[{k:'BRD',v:'15min'},{k:'CODE',v:'30min',c:true}],
    line:'BRD_v3.pdf §4.5 vs. session_config.ts:9', rec:'Reduce session TTL to 15min.', conf:86 },
  { id:'CONF-079', sev:'low', title:'Localization scope ambiguity',
    sources:[{k:'BRD',v:'EN+ES'},{k:'NOTES',v:'EN+ES+FR'}],
    line:'BRD §2 vs. arch_review 12:08', rec:'Confirm FR scope with PM.', conf:74 },
  { id:'CONF-084', sev:'critical', title:'2FA mandatory bypass',
    sources:[{k:'POLICY',v:'mandatory',c:true},{k:'CODE',v:'optional',c:true}],
    line:'privacy_policy §4 vs. mfa_gate.ts:34', rec:'Make 2FA mandatory in v1.', conf:97 },
];

function D2Panel() {
  const [open, setOpen] = useStateP(['CONF-051']);
  const toggle = id => setOpen(o => o.includes(id) ? o.filter(x=>x!==id) : [...o, id]);

  const bySev = D2_CONFLICTS.reduce((a,c)=>{ a[c.sev]=(a[c.sev]||0)+1; return a; },{});
  return (
    <div>
      <PanelHead tag="D2 · DISCOVER" name="Cross-source findings"
        summary="Requirements, rules, and entities extracted from every source and cross-referenced against a shared ontology. Conflicts surface with provenance and a recommended resolution."
        stats={[
          { value:'7',   label:'conflicts' },
          { value:'12',  label:'sources' },
          { value:'2.3s', label:'discover time' },
        ]} />
      <div className="p-7">
        {/* Severity strip */}
        <div className="grid grid-cols-4 gap-px bg-white/5 border hairline rounded-lg overflow-hidden mb-5">
          <SevStat label="Critical" count={bySev.critical||0} active />
          <SevStat label="High"     count={bySev.high||0} />
          <SevStat label="Medium"   count={bySev.medium||0} muted />
          <SevStat label="Low"      count={bySev.low||0} muted />
        </div>

        <div className="space-y-2.5">
          {D2_CONFLICTS.map(c => {
            const isOpen = open.includes(c.id);
            const sevTone = c.sev === 'critical' ? 'border-flame/60' : c.sev === 'high' ? 'border-flame/30' : 'hairline';
            return (
              <div key={c.id} className={`border ${sevTone} bg-ink-900 rounded-lg overflow-hidden ${isOpen ? 'shadow-flame' : ''}`}>
                <button onClick={()=>toggle(c.id)} className="w-full flex items-center gap-4 px-5 py-4 text-left hover:bg-ink-850/50 transition">
                  <SevDot sev={c.sev}/>
                  <span className="num text-[11px] text-ink-400">{c.id}</span>
                  <span className="text-[14.5px] text-ink-50 font-medium flex-1 truncate">{c.title}</span>
                  <span className="hidden sm:flex items-center gap-1">
                    {c.sources.map((s,i)=><Tag key={i} tone={s.c ? 'flame':'default'}>{s.k}</Tag>)}
                  </span>
                  <span className="num text-[11.5px] text-ink-300 w-12 text-right">{c.conf}%</span>
                  <CD size={16} strokeWidth={1.8} className={`text-ink-400 transition ${isOpen ? 'rotate-180':''}`}/>
                </button>
                {isOpen && (
                  <div className="px-5 pb-5 pt-1 border-t hairline">
                    <div className="num text-[11.5px] text-ink-400 mt-3">{c.line}</div>
                    <div className="mt-3 grid sm:grid-cols-3 gap-2">
                      {c.sources.map((s,i)=>(
                        <div key={i} className={`rounded-md p-3 border ${s.c ? 'border-flame/40 bg-flame/[0.04]' : 'hairline bg-ink-850/60'}`}>
                          <div className="flex items-center justify-between"><Tag tone={s.c?'flame':'default'}>{s.k}</Tag><span className={`num text-[12.5px] ${s.c?'text-flame':'text-ink-100'}`}>{s.v}</span></div>
                        </div>
                      ))}
                    </div>
                    <div className="mt-4 flex items-start gap-3 text-[13px]">
                      <WF size={14} strokeWidth={1.8} className="text-flame mt-0.5 shrink-0"/>
                      <span className="text-ink-200"><span className="text-ink-400 uppercase tracking-[0.18em] text-[10.5px] mr-2">RESOLUTION</span>{c.rec}</span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function SevDot({ sev }) {
  const cls = sev==='critical' ? 'bg-flame shadow-[0_0_8px_2px_rgba(255,122,58,.5)]' :
              sev==='high' ? 'bg-flame' :
              sev==='medium' ? 'bg-ink-200' : 'bg-ink-500';
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${cls}`}></span>;
}
function SevStat({ label, count, active, muted }) {
  return (
    <div className={`p-4 ${active ? 'bg-flame/10' : 'bg-ink-900'}`}>
      <div className={`num text-[28px] font-semibold leading-none ${muted ? 'text-ink-300' : active ? 'text-flame' : 'text-ink-50'}`}>{count}</div>
      <div className="mt-1.5 text-[10.5px] uppercase tracking-[0.18em] text-ink-400">{label}</div>
    </div>
  );
}

// ───────────────────────────────────────────────── D3 DESIGN ───
function D3Panel() {
  return (
    <div>
      <PanelHead tag="D3 · DESIGN" name="System architecture"
        summary="Service decomposition, schema, contracts, and auth model — grounded in the requirements D2 produced. Every interface cites the requirements it satisfies."
        stats={[{ value:'4', label:'services' },{ value:'12', label:'entities' },{ value:'23', label:'endpoints' },{ value:'6', label:'events' }]} />
      <div className="p-7 grid lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7 bg-ink-900 border hairline rounded-lg p-5">
          <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400 mb-4">System diagram</div>
          <ArchDiagram />
        </div>
        <div className="lg:col-span-5 space-y-3">
          <div className="bg-ink-900 border hairline rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2.5 border-b hairline">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ink-400"><CO size={11} strokeWidth={2}/> openapi · auth.yaml</div>
              <Tag tone="ghost">23 paths</Tag>
            </div>
            <pre className="px-4 py-3 text-[11.5px] num leading-relaxed text-ink-200 overflow-x-auto"><code>{`paths:
  /auth/login:
    post:
      summary: Begin authentication
      requirements: [req-2147, req-2151]
      requestBody:
        $ref: '#/components/LoginInput'
      responses:
        '200': { $ref: '#/components/MFAChallenge' }
        '423': { description: 'Locked' }   # req-2147
  /auth/verify:
    post:
      summary: Verify MFA challenge
      requirements: [req-2148, req-2160]
...`}</code></pre>
          </div>
          <div className="bg-ink-900 border hairline rounded-lg p-4">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Decisions captured</div>
            <ul className="mt-3 space-y-2 text-[12.5px] text-ink-200">
              <li className="flex items-start gap-2"><CK size={14} className="text-flame mt-0.5 shrink-0"/>MAX_RETRIES = 5 (from CONF-047)</li>
              <li className="flex items-start gap-2"><CK size={14} className="text-flame mt-0.5 shrink-0"/>2FA mandatory (from CONF-084)</li>
              <li className="flex items-start gap-2"><CK size={14} className="text-flame mt-0.5 shrink-0"/>PII encrypted at rest (from CONF-051)</li>
              <li className="flex items-start gap-2"><CK size={14} className="text-flame mt-0.5 shrink-0"/>Session TTL 15min (from CONF-072)</li>
              <li className="flex items-start gap-2"><CK size={14} className="text-flame mt-0.5 shrink-0"/>KYC blocks activation (from CONF-068)</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}

function ArchDiagram() {
  // Hand-drawn SVG architecture: client → gateway → 4 services → DB + KMS
  return (
    <svg viewBox="0 0 600 340" className="w-full h-auto">
      <defs>
        <marker id="arr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="rgba(255,255,255,0.45)"/>
        </marker>
      </defs>
      {/* Client */}
      <ArchNode x={30} y={140} w={100} h={60} title="Mobile" sub="React Native"/>
      {/* Gateway */}
      <ArchNode x={180} y={140} w={110} h={60} title="API Gateway" sub="OAuth2 · rate" flame/>
      {/* Services column */}
      <ArchNode x={340} y={20}  w={120} h={56} title="Auth Service" sub="req-2147..2160"/>
      <ArchNode x={340} y={100} w={120} h={56} title="KYC Service" sub="req-2210..2224"/>
      <ArchNode x={340} y={180} w={120} h={56} title="Session Svc" sub="req-2401..2412"/>
      <ArchNode x={340} y={260} w={120} h={56} title="Audit Log"   sub="req-2901..2908"/>
      {/* Data */}
      <ArchNode x={500} y={60}  w={80}  h={56} title="Postgres" sub="encrypted"/>
      <ArchNode x={500} y={140} w={80}  h={56} title="KMS" sub="field keys" flame/>
      <ArchNode x={500} y={220} w={80}  h={56} title="Redis" sub="sessions"/>
      {/* lines */}
      {[
        ['M130 170 L180 170'],
        ['M290 170 C 310 170, 320 48, 340 48'],
        ['M290 170 C 310 170, 320 128, 340 128'],
        ['M290 170 L340 208'],
        ['M290 170 C 310 170, 320 288, 340 288'],
        ['M460 48 L500 88'],   // auth → pg
        ['M460 128 L500 168'], // kyc → kms
        ['M460 208 L500 248'], // session → redis
        ['M460 48 C 480 48, 480 168, 500 168'], // auth → kms
      ].map((d,i)=>(<path key={i} d={d[0]} stroke="rgba(255,255,255,0.25)" strokeWidth="1.2" fill="none" markerEnd="url(#arr)"/>))}
    </svg>
  );
}
function ArchNode({ x, y, w, h, title, sub, flame }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="6"
        fill={flame ? 'rgba(255,122,58,0.06)' : 'rgba(255,255,255,0.025)'}
        stroke={flame ? 'rgba(255,122,58,0.5)' : 'rgba(255,255,255,0.15)'} strokeWidth="1"/>
      <text x={x + w/2} y={y + h/2 - 4} textAnchor="middle" fontFamily="Space Grotesk" fontSize="13" fontWeight="600"
        fill={flame ? '#ff9560' : '#e7e7ea'}>{title}</text>
      <text x={x + w/2} y={y + h/2 + 12} textAnchor="middle" fontFamily="JetBrains Mono" fontSize="9"
        fill="rgba(255,255,255,0.45)">{sub}</text>
    </g>
  );
}

// ───────────────────────────────────────────────── D4 PROTOTYPE ───
const D4_COMMENTS = [
  { who:'Priya (PM)',   when:'4m',  msg:'Love this — but the "Trouble signing in?" link feels buried. Can it be a button row?', pin:{x:50,y:75} },
  { who:'Marcus (CTO)', when:'12m', msg:'Confirm: 5 retries shown in the lockout state. Looks right.', pin:{x:50,y:55} },
  { who:'Devi (UX)',    when:'1h',  msg:'Letterspacing on the headline is a touch wide — design will tighten.', pin:{x:50,y:22} },
];

function D4Panel() {
  return (
    <div>
      <PanelHead tag="D4 · PROTOTYPE" name="Stakeholder-ready prototype"
        summary="A clickable demo published 18 hours after kickoff. Inline comments from stakeholders flow back into D2 as new constraints — no Powerpoint round-trip."
        stats={[{ value:'7', label:'screens' },{ value:'14', label:'comments' },{ value:'v3', label:'iteration' }]} />
      <div className="p-7 grid lg:grid-cols-12 gap-5">
        {/* Phone mock */}
        <div className="lg:col-span-5 flex justify-center">
          <PhoneMock />
        </div>
        {/* Comments + screens */}
        <div className="lg:col-span-7 space-y-3">
          <div className="bg-ink-900 border hairline rounded-lg p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Stakeholder feedback</div>
              <Tag tone="flame">3 new</Tag>
            </div>
            <div className="space-y-3">
              {D4_COMMENTS.map(c => (
                <div key={c.who} className="flex items-start gap-3 pb-3 border-b hairline last:border-b-0 last:pb-0">
                  <div className="w-7 h-7 rounded-full bg-ink-800 border hairline-strong flex items-center justify-center text-[11px] num text-ink-200 shrink-0">{c.who.split(' ')[0][0]}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 text-[11.5px]"><span className="text-ink-100 font-medium">{c.who}</span><span className="num text-ink-400">{c.when} ago</span></div>
                    <div className="mt-1 text-[13px] text-ink-200 leading-relaxed">{c.msg}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="bg-ink-900 border hairline rounded-lg p-5">
            <div className="text-[11px] uppercase tracking-[0.18em] text-ink-400 mb-3">Screens</div>
            <div className="grid grid-cols-7 gap-2">
              {['Login','MFA','Lockout','KYC start','KYC scan','KYC review','Home'].map((s,i)=>(
                <div key={s} className={`aspect-[9/16] rounded border ${i===0?'border-flame':'hairline'} bg-ink-850 flex items-end p-1.5`}>
                  <div className="text-[9px] num text-ink-300 truncate">{i+1}. {s}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function PhoneMock() {
  return (
    <div className="relative w-[240px] h-[480px] rounded-[36px] bg-ink-900 border hairline-strong p-2 shadow-flame">
      <div className="absolute top-1 left-1/2 -translate-x-1/2 w-20 h-5 bg-ink-950 rounded-b-2xl z-10"/>
      <div className="w-full h-full rounded-[28px] bg-ink-950 overflow-hidden relative">
        <div className="bg-grid absolute inset-0 opacity-40"/>
        <div className="relative px-5 pt-12 pb-5 h-full flex flex-col">
          <div className="text-[10px] num uppercase tracking-[0.22em] text-flame">Acme</div>
          <h2 className="display mt-3 text-[22px] font-semibold tracking-tight leading-tight text-ink-50">Welcome<br/>back.</h2>
          <p className="mt-2 text-[10.5px] text-ink-300">Sign in to continue</p>
          <div className="mt-5 space-y-2.5">
            <div className="border hairline-strong rounded-lg px-3 py-2.5 text-[11px] text-ink-300">Email or phone</div>
            <div className="border hairline-strong rounded-lg px-3 py-2.5 text-[11px] text-ink-300">Password</div>
            <div className="bg-flame text-ink-950 rounded-lg px-3 py-2.5 text-[11px] font-semibold text-center">Continue</div>
            <div className="text-center text-[10px] text-ink-400 mt-3">Trouble signing in?</div>
          </div>
          <div className="mt-auto pt-4 border-t hairline text-[9px] num text-ink-400 text-center">v3 · req-2147 · 2FA mandatory</div>
          {/* pin */}
          <div className="absolute right-3 top-[40%] w-5 h-5 rounded-full bg-flame text-ink-950 text-[10px] font-bold flex items-center justify-center shadow-flame">2</div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { D1Panel, D2Panel, D3Panel, D4Panel, PanelHead, Tag });
