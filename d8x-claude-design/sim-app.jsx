// Simulation app: state machine, pipeline rail, header, approval bar
const { useState, useEffect, useRef, useMemo } = React;

const {
  ArrowRight, ArrowUpRight, Check, X, ChevronRight, ChevronDown,
  FileText, Search, Shapes, Zap, Layers, GitPullReq, Shield, Rocket,
  Workflow, Eye, Activity, Lock, Alert, Plus
} = window.Icons;

const { D1Panel, D2Panel, D3Panel, D4Panel, D5Panel, D6Panel, D7Panel, D8Panel } = window;

const AGENTS = [
  { id:'D1', tag:'INGEST',    name:'Ingest sources',           icon: FileText,  Panel: D1Panel, blurb:'Parse every artifact into structured docs with line-level provenance.', dur: 2200 },
  { id:'D2', tag:'DISCOVER',  name:'Find contradictions',      icon: Search,    Panel: D2Panel, blurb:'Cross-reference requirements across sources; surface conflicts with confidence scores.', dur: 2300, hero:true },
  { id:'D3', tag:'DESIGN',    name:'Architect the system',     icon: Shapes,    Panel: D3Panel, blurb:'Generate services, schema, contracts, and auth model from the resolved requirements.', dur: 1800 },
  { id:'D4', tag:'PROTOTYPE', name:'Ship a clickable demo',    icon: Zap,       Panel: D4Panel, blurb:'Publish an interactive prototype with stakeholder comment threads.', dur: 1600 },
  { id:'D5', tag:'PLAN',      name:'Sequence the backlog',     icon: Layers,    Panel: D5Panel, blurb:'Break scope into epics and dependency-ordered user stories with estimates.', dur: 1400 },
  { id:'D6', tag:'BUILD',     name:'Open pull requests',       icon: GitPullReq, Panel: D6Panel, blurb:'Implement against your repo; every PR cites the requirements and conflicts it resolved.', dur: 2600 },
  { id:'D7', tag:'TEST',      name:'Verify everything',        icon: Shield,    Panel: D7Panel, blurb:'Unit, integration, E2E, SAST, and a11y scans; findings post back to each PR.', dur: 2000 },
  { id:'D8', tag:'SHIP',      name:'Deploy and observe',       icon: Rocket,    Panel: D8Panel, blurb:'Promote through environments with health gates; production telemetry loops back to D2.', dur: 1700 },
];

// Initial state: D1+D2 approved, D3 awaiting approval, rest locked
const INITIAL = {
  D1: { status:'approved', approvedBy:'You',        approvedAt:'2h ago', ran:'4.2s' },
  D2: { status:'approved', approvedBy:'You',        approvedAt:'1h ago', ran:'2.3s', note:'7 conflicts resolved' },
  D3: { status:'awaiting', ran:'1.8s' },
  D4: { status:'locked' },
  D5: { status:'locked' },
  D6: { status:'locked' },
  D7: { status:'locked' },
  D8: { status:'locked' },
};

function App() {
  const [state, setState] = useState(INITIAL);
  const [active, setActive] = useState('D3');
  const [showAnnotate, setShowAnnotate] = useState(false);
  const [showSendBack, setShowSendBack] = useState(false);
  const [toast, setToast] = useState(null);

  const activeAgent = AGENTS.find(a => a.id === active);
  const activeState = state[active];

  // After approval, find next locked agent and start it running
  function approve(id) {
    const idx = AGENTS.findIndex(a => a.id === id);
    setState(s => ({
      ...s,
      [id]: { ...s[id], status:'approved', approvedBy:'You', approvedAt:'just now' }
    }));
    setToast({ kind:'approved', msg:`${id} approved · advancing to ${AGENTS[idx+1]?.id || 'done'}` });

    const next = AGENTS[idx+1];
    if (next) {
      // start "running" on next agent
      setState(s => ({ ...s, [next.id]: { ...s[next.id], status:'running' } }));
      setActive(next.id);
      setTimeout(() => {
        setState(s => ({ ...s, [next.id]: { status:'awaiting', ran:(next.dur/1000).toFixed(1)+'s' } }));
        setToast({ kind:'awaiting', msg:`${next.id} produced an artifact · awaiting your review` });
      }, next.dur);
    } else {
      setToast({ kind:'done', msg:'Run #4129 complete · all 8 agents approved' });
    }
  }

  function sendBack(id, reason) {
    setState(s => ({ ...s, [id]: { ...s[id], status:'running' } }));
    setToast({ kind:'re-run', msg:`${id} re-running with feedback: "${reason}"` });
    setTimeout(() => {
      setState(s => ({ ...s, [id]: { status:'awaiting', ran:'1.6s' } }));
      setToast({ kind:'awaiting', msg:`${id} returned · review the diff` });
    }, 2000);
    setShowSendBack(false);
  }

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(()=>setToast(null), 4000);
    return ()=>clearTimeout(t);
  }, [toast]);

  return (
    <div className="min-h-screen flex flex-col">
      <Header/>
      <div className="flex-1 grid grid-cols-[300px_1fr] min-h-0">
        <Sidebar agents={AGENTS} state={state} active={active} onSelect={setActive}/>
        <Main agent={activeAgent} agentState={activeState} state={state}
          onApprove={()=>approve(active)}
          onAnnotate={()=>setShowAnnotate(true)}
          onSendBack={()=>setShowSendBack(true)} />
      </div>
      {showAnnotate && <AnnotateModal agentId={active} onClose={()=>setShowAnnotate(false)}/>}
      {showSendBack && <SendBackModal agentId={active} onClose={()=>setShowSendBack(false)} onSubmit={(reason)=>sendBack(active, reason)}/>}
      {toast && <Toast {...toast}/>}
    </div>
  );
}

// ───────────────────────────────────────────────────── HEADER ───
function Header() {
  return (
    <header className="h-14 border-b hairline bg-ink-950 flex items-center px-4 sticky top-0 z-30">
      <a href="index.html" className="flex items-center gap-2 group">
        <Logo/>
        <span className="display text-[17px] font-semibold tracking-tight">D8X</span>
      </a>
      <span className="mx-4 w-px h-5 bg-white/10"/>
      <div className="flex items-center gap-3 min-w-0">
        <span className="num text-[11px] uppercase tracking-[0.18em] text-ink-400">Engagement</span>
        <span className="text-[13.5px] text-ink-50 font-medium truncate">Acme Banking — Mobile auth uplift</span>
        <span className="num text-[10.5px] uppercase tracking-[0.18em] text-ink-400 border hairline rounded px-1.5 py-0.5">Run #4129</span>
      </div>
      <div className="ml-auto flex items-center gap-3">
        <div className="hidden md:flex items-center gap-2 text-[11.5px]">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full rounded-full bg-flame opacity-60 animate-ping"></span>
            <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-flame"></span>
          </span>
          <span className="text-ink-200">Live</span>
          <span className="num text-ink-400">started 2h 14m ago</span>
        </div>
        <span className="hidden lg:inline-flex w-px h-5 bg-white/10"/>
        <div className="hidden lg:flex items-center gap-2">
          <div className="flex -space-x-1.5">
            <Avatar c="P"/>
            <Avatar c="M"/>
            <Avatar c="Y"/>
          </div>
          <span className="text-[12px] text-ink-300">3 watching</span>
        </div>
        <a href="index.html" className="text-[12.5px] text-ink-300 hover:text-ink-50 border hairline rounded px-2.5 py-1.5 transition flex items-center gap-1.5">
          <ArrowUpRight size={12} strokeWidth={2}/> Back to overview
        </a>
      </div>
    </header>
  );
}

function Avatar({ c }) {
  return (
    <span className="w-6 h-6 rounded-full bg-ink-800 border border-ink-950 flex items-center justify-center text-[10px] num text-ink-100">{c}</span>
  );
}

function Logo() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <rect x="1.5" y="1.5" width="21" height="21" rx="4" stroke="currentColor" strokeOpacity=".5" strokeWidth="1.4"/>
      <circle cx="9.5" cy="9.5" r="2.4" stroke="#ff7a3a" strokeWidth="1.6"/>
      <circle cx="14.5" cy="14.5" r="2.4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M14.5 9.5h2.5M9.5 14.5H7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

// ───────────────────────────────────────────────────── SIDEBAR ───
function Sidebar({ agents, state, active, onSelect }) {
  // Pipeline progress
  const totalApproved = agents.filter(a => state[a.id].status === 'approved').length;
  return (
    <aside className="border-r hairline bg-ink-900/40 overflow-y-auto">
      <div className="p-5 border-b hairline">
        <div className="flex items-center justify-between">
          <span className="num text-[10.5px] uppercase tracking-[0.18em] text-ink-400">Pipeline</span>
          <span className="num text-[10.5px] text-ink-300">{totalApproved}/{agents.length}</span>
        </div>
        <div className="mt-2 h-1 bg-ink-800 rounded-full overflow-hidden">
          <div className="h-full bg-flame transition-all duration-500" style={{ width: `${(totalApproved/agents.length)*100}%` }}/>
        </div>
      </div>

      <ol className="px-2 py-3 relative">
        {/* Vertical rail */}
        <div className="absolute left-[28px] top-6 bottom-6 w-px bg-white/10" aria-hidden/>
        {agents.map((a, i) => (
          <li key={a.id}>
            <AgentRow agent={a} st={state[a.id]} active={active===a.id} onClick={()=>onSelect(a.id)}/>
            {i < agents.length - 1 && (
              <GateConnector approved={state[a.id].status==='approved'}/>
            )}
          </li>
        ))}
      </ol>
    </aside>
  );
}

function AgentRow({ agent, st, active, onClick }) {
  const isLocked = st.status === 'locked';
  const Ic = agent.icon;
  return (
    <button onClick={onClick}
      className={`relative w-full text-left flex items-start gap-3 px-3 py-3 rounded-md transition ${
        active ? 'bg-ink-850' : 'hover:bg-ink-900/70'
      } ${isLocked ? 'opacity-50' : ''}`}>
      <NodeMark status={st.status} icon={Ic} active={active} hero={agent.hero}/>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="num text-[10.5px] text-ink-400">{agent.id}</span>
          <span className="num text-[9.5px] uppercase tracking-[0.18em] text-ink-300">{agent.tag}</span>
        </div>
        <div className={`mt-0.5 text-[13px] font-medium leading-tight ${active ? 'text-ink-50' : 'text-ink-100'}`}>{agent.name}</div>
        <div className="mt-1.5"><StatusPill status={st.status} ran={st.ran} note={st.note}/></div>
      </div>
    </button>
  );
}

function NodeMark({ status, icon: Ic, active, hero }) {
  // Centered on the rail line at left:28px (so 12px left + ~16px center)
  let inner = null, ring = '';
  if (status === 'approved') {
    inner = <Check size={13} strokeWidth={2.4}/>;
    ring = 'bg-flame text-ink-950 border border-flame';
  } else if (status === 'awaiting') {
    inner = <Ic size={13} strokeWidth={1.8}/>;
    ring = 'bg-ink-950 text-flame border border-flame shadow-flame';
  } else if (status === 'running') {
    inner = <Spinner/>;
    ring = 'bg-ink-950 text-flame border border-flame/60';
  } else {
    inner = <Lock size={11} strokeWidth={1.8}/>;
    ring = 'bg-ink-900 text-ink-400 border hairline';
  }
  return (
    <div className={`relative z-10 w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${ring}`}>
      {inner}
    </div>
  );
}

function Spinner() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="animate-spin" style={{ animation:'spin 1s linear infinite' }}>
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2"/>
      <path d="M21 12a9 9 0 00-9-9" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  );
}

function StatusPill({ status, ran, note }) {
  const map = {
    approved: { txt:'Approved', cls:'text-moss bg-moss/10 border border-moss/20' },
    awaiting: { txt:'Awaiting approval', cls:'text-flame bg-flame/10 border border-flame/30' },
    running:  { txt:'Running…', cls:'text-flame bg-flame/5 border border-flame/30' },
    locked:   { txt:'Locked',   cls:'text-ink-400 bg-ink-850 border hairline' },
  }[status];
  return (
    <div className="flex items-center gap-1.5">
      <span className={`text-[10px] num uppercase tracking-[0.16em] px-1.5 py-0.5 rounded ${map.cls}`}>{map.txt}</span>
      {ran && status !== 'running' && <span className="num text-[10px] text-ink-400">{ran}</span>}
      {note && <span className="text-[10px] text-ink-400 truncate">{note}</span>}
    </div>
  );
}

function GateConnector({ approved }) {
  // Approval gate iconography between agents — a thin bracket with a checkmark
  return (
    <div className="relative h-6 flex items-center justify-center pl-[28px] mr-2">
      <div className={`absolute left-[28px] top-0 bottom-0 w-px ${approved ? 'bg-flame' : 'bg-white/10'}`}/>
      <div className={`relative z-10 ml-[-26px] flex items-center gap-1 num text-[8.5px] uppercase tracking-[0.18em] px-1.5 py-0.5 rounded ${
        approved ? 'text-flame bg-flame/5 border border-flame/30' : 'text-ink-400 bg-ink-900 border hairline'
      }`}>
        <GateGlyph small/>
        <span>gate</span>
      </div>
    </div>
  );
}
function GateGlyph({ small }) {
  return (
    <svg width={small?14:18} height={small?8:11} viewBox="0 0 28 14" fill="none">
      <path d="M3 1v12M25 1v12" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
      <path d="M9 7l3 3 7-7" stroke="#ff7a3a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ───────────────────────────────────────────────────── MAIN ───
function Main({ agent, agentState, state, onApprove, onAnnotate, onSendBack }) {
  const isApproved = agentState.status === 'approved';
  const isAwaiting = agentState.status === 'awaiting';
  const isRunning  = agentState.status === 'running';
  const isLocked   = agentState.status === 'locked';

  return (
    <main className="relative overflow-y-auto bg-ink-950">
      <div className="max-w-[1180px] mx-auto pb-32">
        {/* Banner */}
        {isApproved && (
          <Banner tone="moss"
            text={<>You approved <span className="num text-ink-50">{agent.id} · {agent.tag}</span> {agentState.approvedAt}.</>}
            note={agentState.note}/>
        )}
        {isRunning && (
          <Banner tone="flame"
            text={<><span className="num text-ink-50">{agent.id} · {agent.tag}</span> is running…</>}
            progress/>
        )}
        {isLocked && (
          <LockedState agent={agent} prevId={prevAgent(agent.id)?.id} prevStatus={prevAgent(agent.id) && state[prevAgent(agent.id).id].status}/>
        )}

        {/* Panel content */}
        {!isLocked && agent.Panel && (
          <div className="bg-ink-900 border hairline rounded-lg mx-7 mt-5 mb-7 overflow-hidden">
            <agent.Panel/>
          </div>
        )}
      </div>

      {/* Sticky approval bar */}
      {isAwaiting && (
        <ApprovalBar agent={agent} ran={agentState.ran}
          onApprove={onApprove} onAnnotate={onAnnotate} onSendBack={onSendBack}/>
      )}
    </main>
  );
}

function prevAgent(id) {
  const i = AGENTS.findIndex(a=>a.id===id);
  return i > 0 ? AGENTS[i-1] : null;
}

function Banner({ tone, text, note, progress }) {
  const cls = tone==='moss'
    ? 'bg-moss/5 border-moss/30 text-moss'
    : 'bg-flame/5 border-flame/30 text-flame';
  return (
    <div className={`mx-7 mt-7 border ${cls} rounded-lg px-5 py-3.5 flex items-center gap-3`}>
      {tone==='moss' ? <Check size={14} strokeWidth={2.2}/> : <Activity size={14} strokeWidth={2}/>}
      <span className="text-[13px]">{text}</span>
      {note && <span className="ml-1 text-[12px] text-ink-300">· {note}</span>}
      {progress && (
        <div className="ml-auto flex items-center gap-2">
          <div className="w-32 h-1 bg-ink-800 rounded overflow-hidden">
            <div className="h-full bg-flame animate-progressBar" style={{'--dur':'1.8s'}}/>
          </div>
          <span className="num text-[11px] text-ink-300">working…</span>
        </div>
      )}
    </div>
  );
}

function LockedState({ agent, prevId, prevStatus }) {
  return (
    <div className="mx-7 mt-7 border hairline rounded-lg p-12 bg-ink-900 text-center">
      <div className="w-12 h-12 rounded-full bg-ink-850 border hairline-strong flex items-center justify-center mx-auto text-ink-400">
        <Lock size={18} strokeWidth={1.8}/>
      </div>
      <h2 className="display mt-5 text-[22px] font-semibold tracking-tight text-ink-100">
        {agent.id} · {agent.name}
      </h2>
      <p className="mt-2 text-[13.5px] text-ink-300 max-w-[48ch] mx-auto">
        {agent.blurb}
      </p>
      <p className="mt-5 text-[12.5px] num text-ink-400">
        Will start once <span className="text-flame">{prevId}</span> is approved. Current status: <span className="text-ink-200 uppercase tracking-wider">{prevStatus}</span>
      </p>
    </div>
  );
}

// ───────────────────────────────────────────────────── APPROVAL BAR ───
function ApprovalBar({ agent, ran, onApprove, onAnnotate, onSendBack }) {
  return (
    <div className="fixed bottom-0 left-[300px] right-0 z-20">
      <div className="bg-ink-900/90 backdrop-blur-xl border-t border-flame/30">
        <div className="max-w-[1180px] mx-auto px-7 py-4 flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-flame/10 border border-flame/40 flex items-center justify-center text-flame">
              <GateGlyph/>
            </div>
            <div>
              <div className="flex items-center gap-2 text-[10.5px] num uppercase tracking-[0.18em] text-flame">
                Approval gate · {agent.id}
              </div>
              <div className="text-[13.5px] text-ink-50">
                <span className="font-medium">{agent.name}</span> ready for review
              </div>
            </div>
          </div>
          <div className="hidden md:flex items-center gap-4 ml-2 text-[11.5px] num text-ink-400 border-l hairline pl-4">
            <span>ran in <span className="text-ink-100">{ran}</span></span>
            <span>·</span>
            <span>conf <span className="text-ink-100">0.94</span></span>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <button onClick={onSendBack} className="text-[12.5px] text-ink-200 hover:text-ink-50 px-3 py-2 rounded border hairline transition inline-flex items-center gap-1.5">
              <X size={12} strokeWidth={2}/> Send back
            </button>
            <button onClick={onAnnotate} className="text-[12.5px] text-ink-200 hover:text-ink-50 px-3 py-2 rounded border hairline transition inline-flex items-center gap-1.5">
              <Plus size={12} strokeWidth={2}/> Annotate
            </button>
            <button onClick={onApprove} className="text-[13px] font-medium text-ink-950 bg-flame hover:bg-flame-soft px-4 py-2 rounded inline-flex items-center gap-1.5 transition shadow-flame">
              Approve &amp; advance <ArrowRight size={13} strokeWidth={2.4}/>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ───────────────────────────────────────────────────── MODALS ───
function Modal({ children, onClose, title, kicker }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-6 bg-ink-950/70 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-ink-900 border hairline-strong rounded-lg w-full max-w-md shadow-flame" onClick={e=>e.stopPropagation()}>
        <div className="px-5 py-4 border-b hairline flex items-center justify-between">
          <div>
            <div className="num text-[10.5px] uppercase tracking-[0.18em] text-flame">{kicker}</div>
            <div className="display text-[17px] font-semibold tracking-tight">{title}</div>
          </div>
          <button onClick={onClose} className="w-7 h-7 rounded border hairline text-ink-300 hover:text-ink-50 flex items-center justify-center">
            <X size={13} strokeWidth={2}/>
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

function AnnotateModal({ agentId, onClose }) {
  return (
    <Modal kicker={`${agentId} · Add note`} title="Annotate this artifact" onClose={onClose}>
      <p className="text-[13px] text-ink-300 leading-relaxed">
        Notes attach to this run's artifact and become context for downstream agents. They don't trigger a re-run.
      </p>
      <textarea className="w-full mt-4 bg-ink-850 border hairline rounded p-3 text-[13px] text-ink-100 placeholder:text-ink-400 outline-none focus:border-flame/50 transition min-h-[100px]"
        placeholder="e.g. We discussed making KYC step skippable for existing customers — check with compliance before D5."/>
      <div className="mt-4 flex items-center justify-end gap-2">
        <button onClick={onClose} className="text-[12.5px] text-ink-300 hover:text-ink-50 px-3 py-2">Cancel</button>
        <button onClick={onClose} className="text-[12.5px] font-medium text-ink-950 bg-flame hover:bg-flame-soft px-3.5 py-2 rounded">Save note</button>
      </div>
    </Modal>
  );
}

function SendBackModal({ agentId, onClose, onSubmit }) {
  const [reason, setReason] = useState('');
  const presets = [
    'Missed a requirement we discussed in kickoff',
    'Resolution doesn\'t match our compliance posture',
    'Need higher-confidence findings only',
  ];
  return (
    <Modal kicker={`${agentId} · Send back`} title="Re-run with feedback" onClose={onClose}>
      <p className="text-[13px] text-ink-300 leading-relaxed">
        Tell {agentId} what's off. The agent will re-run with your feedback as additional context and produce a new artifact.
      </p>
      <div className="mt-3 space-y-1.5">
        {presets.map(p => (
          <button key={p} onClick={()=>setReason(p)}
            className={`block w-full text-left text-[12.5px] px-3 py-2 rounded border transition ${
              reason===p ? 'border-flame/50 bg-flame/5 text-ink-50' : 'hairline text-ink-200 hover:bg-ink-850'
            }`}>{p}</button>
        ))}
      </div>
      <textarea value={reason} onChange={e=>setReason(e.target.value)}
        className="w-full mt-3 bg-ink-850 border hairline rounded p-3 text-[13px] text-ink-100 placeholder:text-ink-400 outline-none focus:border-flame/50 transition min-h-[80px]"
        placeholder="Or write your own reason…"/>
      <div className="mt-4 flex items-center justify-end gap-2">
        <button onClick={onClose} className="text-[12.5px] text-ink-300 hover:text-ink-50 px-3 py-2">Cancel</button>
        <button onClick={()=>reason && onSubmit(reason)} disabled={!reason}
          className={`text-[12.5px] font-medium px-3.5 py-2 rounded ${
            reason ? 'text-ink-950 bg-flame hover:bg-flame-soft' : 'text-ink-500 bg-ink-800 cursor-not-allowed'
          }`}>Re-run {agentId}</button>
      </div>
    </Modal>
  );
}

function Toast({ kind, msg }) {
  const tone = kind === 'approved' ? 'border-moss/40 text-moss' :
               kind === 'awaiting' ? 'border-flame/40 text-flame' :
               kind === 'done' ? 'border-moss/40 text-moss' :
               'border-flame/40 text-flame';
  return (
    <div className="fixed top-20 right-6 z-50 animate-in">
      <div className={`bg-ink-900 backdrop-blur-xl border ${tone} rounded-md shadow-flame px-4 py-3 flex items-center gap-3 max-w-sm`}>
        {kind === 'approved' || kind === 'done' ? <Check size={14} strokeWidth={2.2}/> : <Activity size={14} strokeWidth={2}/>}
        <span className="text-[13px] text-ink-100">{msg}</span>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App/>);
