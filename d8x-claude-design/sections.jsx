// Top-of-page sections: Nav, Hero, Pipeline (the agents)
const { useState, useEffect, useRef, useMemo } = React;
const {
  ArrowRight, ChevronRight, ChevronDown, Check, X, Plus, Minus, Alert,
  FileText, Mic, Code, Image: ImageI, Video, Search, Shapes, Zap, Server,
  Boxes, GitPullReq, Shield, Rocket, Lock, Eye, Building, Users, Layers,
  Activity, Globe, ArrowUpRight, Workflow, Gauge, Terminal, Sliders
} = window.Icons;

// ─────────────────────────────────────────── NAV ───
function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <header className={`fixed top-0 inset-x-0 z-50 transition-all duration-300 ${
      scrolled ? 'backdrop-blur-xl bg-ink-950/75 border-b hairline' : 'bg-transparent border-b border-transparent'
    }`}>
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8 h-16 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2 group">
          <Logo />
          <span className="display text-[19px] font-semibold tracking-tight">D8X</span>
          <span className="hidden md:inline-flex items-center text-[10px] font-medium uppercase tracking-[0.18em] text-ink-300 ml-2 px-1.5 py-0.5 border hairline rounded">
            v1.0
          </span>
        </a>
        <nav className="hidden lg:flex items-center gap-8 text-[13.5px] text-ink-200">
          <a href="#product" className="hover:text-ink-50 transition">Product</a>
          <a href="#agents" className="hover:text-ink-50 transition">Agents</a>
          <a href="#how" className="hover:text-ink-50 transition">How it works</a>
          <a href="#pricing" className="hover:text-ink-50 transition">Pricing</a>
          <a href="#" className="hover:text-ink-50 transition">Docs</a>
        </nav>
        <div className="flex items-center gap-2.5">
          <a href="#" className="hidden sm:inline-flex text-[13.5px] text-ink-200 hover:text-ink-50 transition px-3 py-1.5">Sign in</a>
          <a href="#demo" className="inline-flex items-center gap-1.5 text-[13.5px] font-medium bg-flame text-ink-950 px-3.5 py-2 rounded hover:bg-flame-soft transition">
            Book a demo <ArrowRight size={14} strokeWidth={2.2} />
          </a>
        </div>
      </div>
    </header>
  );
}

function Logo() {
  // D8X mark: a square with a stylized "8" of two stacked circles + an offset corner suggesting flow
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="1.5" y="1.5" width="21" height="21" rx="4" stroke="currentColor" strokeOpacity=".5" strokeWidth="1.4"/>
      <circle cx="9.5" cy="9.5" r="2.4" stroke="#ff7a3a" strokeWidth="1.6"/>
      <circle cx="14.5" cy="14.5" r="2.4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M14.5 9.5h2.5M9.5 14.5H7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

// ─────────────────────────────────────────── HERO ───
function Hero() {
  return (
    <section id="top" className="relative pt-32 pb-20 lg:pt-40 lg:pb-28 overflow-hidden">
      {/* Subtle grid + radial fade */}
      <div className="absolute inset-0 bg-grid opacity-60 [mask-image:radial-gradient(ellipse_at_top,black_30%,transparent_70%)]" />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-flame/30 to-transparent" />

      <div className="relative max-w-[1280px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-12 gap-10 lg:gap-14 items-center">
          {/* Copy */}
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 text-[11.5px] uppercase tracking-[0.18em] text-ink-300 border hairline rounded-full px-3 py-1.5 mb-7">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full rounded-full bg-flame opacity-60 animate-ping"></span>
                <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-flame"></span>
              </span>
              Patent pending — cross-source conflict detection
            </div>

            <h1 className="display text-[44px] sm:text-[58px] lg:text-[72px] leading-[0.98] font-semibold tracking-[-0.035em]">
              Catch the contradictions<br/>
              <span className="text-ink-300">your team </span>
              <span className="relative">
                <span className="relative z-10">cannot</span>
                <span className="absolute inset-x-0 bottom-1.5 h-[6px] bg-flame/30 -z-0" aria-hidden></span>
              </span>
              <span className="text-ink-300">.</span>
            </h1>

            <p className="mt-7 max-w-[560px] text-[17px] leading-[1.55] text-ink-200">
              D8X is the only agentic SDLC platform that automatically finds
              contradictions across your <span className="text-ink-50">BRDs</span>, <span className="text-ink-50">source code</span>,
              and <span className="text-ink-50">meeting notes</span> — before they become production incidents.
              Reclaim the <span className="num text-flame font-medium">40 hours a week</span> your architects spend reconciling them by hand.
            </p>

            <div className="mt-9 flex flex-wrap items-center gap-3">
              <a href="simulation.html" className="group inline-flex items-center gap-2 bg-flame text-ink-950 px-5 py-3 rounded font-medium text-[14.5px] hover:bg-flame-soft transition">
                Try the live simulation
                <ArrowRight size={16} strokeWidth={2.2} className="group-hover:translate-x-0.5 transition" />
              </a>
              <a href="#demo" className="group inline-flex items-center gap-2 border hairline-strong text-ink-100 px-5 py-3 rounded font-medium text-[14.5px] hover:bg-ink-850 transition">
                Book a demo
                <ArrowUpRight size={16} strokeWidth={2} className="text-ink-300 group-hover:text-flame transition" />
              </a>
            </div>

            <div className="mt-12 grid grid-cols-3 gap-6 max-w-[460px]">
              <Stat n="8" label="specialized agents" />
              <Stat n="40h" label="reclaimed weekly" />
              <Stat n="100%" label="audit trail" />
            </div>
          </div>

          {/* Visual: 3 sources → flagged contradiction */}
          <div className="lg:col-span-5">
            <ConflictHeroVisual />
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({ n, label }) {
  return (
    <div className="border-l hairline-strong pl-4">
      <div className="num text-[28px] font-semibold text-ink-50 leading-none">{n}</div>
      <div className="mt-2 text-[12px] text-ink-300 leading-tight">{label}</div>
    </div>
  );
}

function ConflictHeroVisual() {
  return (
    <div className="relative aspect-[1/1.05] w-full max-w-[440px] mx-auto">
      {/* Three source documents arrayed at top, converging on a flagged conflict */}
      <svg className="absolute inset-0 w-full h-full" viewBox="0 0 440 460" fill="none" aria-hidden>
        {/* connecting lines from doc bottoms to central flag */}
        <defs>
          <linearGradient id="line1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(255,255,255,0.18)"/>
            <stop offset="100%" stopColor="#ff7a3a"/>
          </linearGradient>
          <pattern id="dotline" x="0" y="0" width="4" height="4" patternUnits="userSpaceOnUse">
            <circle cx="2" cy="2" r="0.7" fill="rgba(255,255,255,0.35)"/>
          </pattern>
        </defs>
        <path d="M70 120 C 90 200, 160 240, 220 290" stroke="url(#line1)" strokeWidth="1.2"/>
        <path d="M220 120 C 220 180, 220 220, 220 280" stroke="url(#line1)" strokeWidth="1.2"/>
        <path d="M370 120 C 350 200, 280 240, 220 290" stroke="url(#line1)" strokeWidth="1.2"/>
      </svg>

      {/* Doc cards (positioned absolutely) */}
      <DocCard className="absolute left-0 top-2 -rotate-[6deg]" type="brd"
        title="BRD_v3.pdf" line="L47" snippet={'"Maximum retry attempts: 3"'} />
      <DocCard className="absolute left-1/2 -translate-x-1/2 top-0" type="code"
        title="auth_service.py" line="L122" snippet={'MAX_RETRIES = 5'} />
      <DocCard className="absolute right-0 top-2 rotate-[6deg]" type="notes"
        title="kickoff_2026-04-02.txt" line="00:23:14" snippet={'"...let\'s go with five..."'} />

      {/* Central flag / contradiction card */}
      <div className="absolute left-1/2 -translate-x-1/2 top-[58%] w-[88%] max-w-[400px]">
        <div className="relative bg-ink-900 border border-flame/60 shadow-flame rounded-md overflow-hidden">
          <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-flame to-transparent"/>
          <div className="px-4 py-2.5 flex items-center justify-between border-b border-flame/30 bg-flame/5">
            <div className="flex items-center gap-2 text-[11.5px] uppercase tracking-[0.16em] text-flame font-medium">
              <Alert size={13} strokeWidth={2}/> Contradiction detected
            </div>
            <span className="num text-[10.5px] text-flame/80">CONF #047</span>
          </div>
          <div className="p-4 space-y-2.5">
            <div className="text-[13px] text-ink-100 leading-snug">
              Three sources disagree on retry policy.
            </div>
            <div className="space-y-1 text-[12px]">
              <Row src="BRD" val="3" agree={false}/>
              <Row src="code" val="5" agree={true}/>
              <Row src="notes" val="5 (verbal)" agree={true}/>
            </div>
            <div className="pt-2 border-t hairline flex items-center justify-between text-[11.5px]">
              <span className="text-ink-300">Confidence <span className="num text-ink-100">94%</span></span>
              <span className="text-flame inline-flex items-center gap-1">Resolve <ArrowRight size={12} strokeWidth={2}/></span>
            </div>
          </div>
        </div>
        <div className="mt-2 text-[11px] num text-ink-400 text-center">
          d2_discover · run #4129 · 2.3s
        </div>
      </div>
    </div>
  );
}

function DocCard({ className, type, title, line, snippet }) {
  const Ico = type === 'brd' ? FileText : type === 'code' ? Code : Mic;
  const tag = type === 'brd' ? 'PDF' : type === 'code' ? 'PY' : 'AUDIO';
  return (
    <div className={`w-[150px] bg-ink-850 border hairline-strong rounded-md p-2.5 shadow-card ${className}`}>
      <div className="flex items-center gap-1.5 text-[10.5px] text-ink-300">
        <Ico size={11} strokeWidth={1.8}/>
        <span className="truncate font-medium text-ink-100">{title}</span>
      </div>
      <div className="mt-1.5 text-[10px] num text-ink-400 flex items-center justify-between">
        <span>{line}</span>
        <span className="text-[8.5px] tracking-widest text-ink-300">{tag}</span>
      </div>
      <div className={`mt-1.5 text-[11px] num leading-snug ${type==='code' ? 'text-flame' : 'text-ink-200'}`}>
        {snippet}
      </div>
    </div>
  );
}

function Row({ src, val, agree }) {
  return (
    <div className="flex items-center justify-between font-mono">
      <span className="text-ink-400">{src}</span>
      <span className={`px-1.5 py-0.5 rounded ${agree ? 'text-ink-100 bg-ink-800' : 'text-flame bg-flame/10'}`}>{val}</span>
    </div>
  );
}

// ─────────────────────────────────────────── PIPELINE ───
const AGENTS = [
  { id:'D1', name:'Ingest',    tag:'parse',     icon: FileText, blurb:'Parses any input format', detail:'Connect any source — PDFs, DOCX, Markdown, source code, screenshots, meeting recordings, even Loom videos. D1 normalizes everything into structured documents with line-level provenance for downstream agents.', tags:['PDF','DOCX','MP3','MP4','GitHub','Figma'] },
  { id:'D2', name:'Discover',  tag:'reconcile', icon: Search,   blurb:'Extracts requirements & finds CONFLICTS', detail:'The patented core. D2 extracts requirements, business rules, and entities — then cross-references them across every source you’ve connected. It surfaces direct contradictions, semantic mismatches, and ambiguous handoffs your team would miss.', tags:['Conflicts','Entities','Rules','Lineage'], hero:true },
  { id:'D3', name:'Design',    tag:'architect', icon: Shapes,   blurb:'Architecture, schema, contracts', detail:'Generates system architecture, database schema, API contracts, auth model, and frontend component boundaries — grounded in the requirements D2 produced.', tags:['ERD','OpenAPI','Auth','UI tree'] },
  { id:'D4', name:'Prototype', tag:'demo',      icon: Zap,      blurb:'Interactive demo for stakeholders', detail:'Spins up a clickable prototype the day after kickoff. Stakeholders leave inline feedback that flows straight back into D2 as new constraints.', tags:['Clickable','Inline notes','Versioned'] },
  { id:'D5', name:'Plan',      tag:'sequence',  icon: Layers,   blurb:'Epics & sequenced user stories', detail:'Breaks scope into epics, sequences user stories with dependency-aware ordering, and assigns acceptance criteria you can review before any line of code is written.', tags:['Epics','Stories','AC','Estimates'] },
  { id:'D6', name:'Build',     tag:'code',      icon: GitPullReq, blurb:'Code generation, GitHub PRs', detail:'Writes feature branches and opens pull requests against your repo. Every PR cites the requirement IDs it implements and the conflicts it resolved along the way.', tags:['PRs','Branches','Lineage'] },
  { id:'D7', name:'Test',      tag:'verify',    icon: Shield,   blurb:'QA, security, a11y, coverage', detail:'Runs unit, integration, and end-to-end tests, plus security and accessibility scans. Coverage and findings post back to the PR before any human review.', tags:['Unit','E2E','SAST','a11y'] },
  { id:'D8', name:'Ship',      tag:'deploy',    icon: Rocket,   blurb:'Deploy and monitor', detail:'Promotes through your environments, watches the rollout, and feeds production telemetry back into D2 so future requirements stay grounded in what actually happened.', tags:['Deploy','Rollback','Telemetry'] },
];

function Pipeline() {
  const [active, setActive] = useState('D2');
  const current = AGENTS.find(a => a.id === active);
  const Ico = current.icon;

  return (
    <section id="agents" className="relative py-24 lg:py-32 border-t hairline">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <SectionLabel num="01" title="The eight agents"
          eyebrow="Pipeline" lead="One handoff per stage. A human-approval gate between each."/>

        {/* The pipeline rail */}
        <div className="mt-14 relative">
          {/* Animated flow dots layer (decorative) */}
          <div className="absolute left-0 right-0 top-[42px] h-[2px] hidden md:block pointer-events-none overflow-hidden">
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent"></div>
            {[0,1,2,3].map(i => (
              <div key={i}
                className="absolute -top-[2px] w-1.5 h-1.5 rounded-full bg-flame shadow-[0_0_8px_2px_rgba(255,122,58,.6)] animate-flow"
                style={{ animationDelay: `${i * 0.8}s` }} />
            ))}
          </div>

          <div className="grid grid-cols-4 md:grid-cols-8 gap-y-6 gap-x-1 relative">
            {AGENTS.map((a, i) => {
              const isActive = a.id === active;
              const isHero = a.hero;
              return (
                <div key={a.id} className="flex flex-col items-center">
                  <button onClick={() => setActive(a.id)}
                    className={`group relative w-full flex flex-col items-center gap-2 transition`}>
                    {/* Node */}
                    <div className={`relative w-[68px] h-[68px] md:w-[74px] md:h-[74px] rounded-md flex items-center justify-center transition
                      ${isActive
                        ? 'bg-flame text-ink-950 shadow-flame'
                        : isHero
                          ? 'bg-ink-850 text-ink-50 border border-flame/40'
                          : 'bg-ink-850 text-ink-200 border hairline-strong group-hover:border-white/25'}`}>
                      {/* tiny corner ID */}
                      <span className={`absolute top-1.5 left-1.5 num text-[9.5px] font-medium tracking-wider
                        ${isActive ? 'text-ink-950/70' : 'text-ink-400'}`}>{a.id}</span>
                      <a.icon size={22} strokeWidth={1.7}/>
                      {/* hero pulse ring when not active */}
                      {isHero && !isActive && (
                        <span className="absolute inset-0 rounded-md animate-pulseRing" />
                      )}
                    </div>
                    <div className="text-center">
                      <div className={`text-[13.5px] font-medium ${isActive ? 'text-ink-50' : 'text-ink-100'}`}>{a.name}</div>
                      <div className={`text-[10.5px] num uppercase tracking-[0.16em] mt-0.5 ${isActive ? 'text-flame' : 'text-ink-400'}`}>{a.tag}</div>
                    </div>
                  </button>

                  {/* Approval gate between this and next */}
                  {i < AGENTS.length - 1 && (
                    <Gate />
                  )}
                </div>
              );
            })}
          </div>

          {/* Approval gates row (desktop, between nodes) — rendered absolutely for alignment */}
        </div>

        {/* Detail card */}
        <div className="mt-12 grid lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 bg-ink-850 border hairline rounded-lg p-6 lg:p-8 relative overflow-hidden">
            <div className="absolute top-0 left-0 h-full w-1 bg-flame"></div>
            <div className="flex items-start gap-4">
              <div className="shrink-0 w-12 h-12 rounded bg-ink-800 border hairline-strong flex items-center justify-center text-ink-100">
                <Ico size={20} strokeWidth={1.7}/>
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-3">
                  <span className="num text-[11px] uppercase tracking-[0.18em] text-flame">{current.id} · {current.tag}</span>
                  {current.hero && <span className="text-[10px] num uppercase tracking-[0.18em] text-ink-950 bg-flame px-1.5 py-0.5 rounded">Patent</span>}
                </div>
                <h3 className="display mt-1 text-[28px] font-semibold leading-tight">{current.name}</h3>
                <p className="mt-3 text-[15px] text-ink-200 leading-relaxed max-w-[60ch]">{current.detail}</p>
                <div className="mt-5 flex flex-wrap gap-1.5">
                  {current.tags.map(t => (
                    <span key={t} className="text-[11.5px] num uppercase tracking-wider text-ink-300 border hairline rounded px-2 py-1">
                      {t}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Approval gate explainer */}
          <div className="lg:col-span-5 bg-ink-900 border hairline rounded-lg p-6 lg:p-8">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ink-300">
              <GateMini /> Approval gate
            </div>
            <h4 className="display mt-2 text-[20px] font-semibold tracking-tight">Every handoff is reviewable.</h4>
            <p className="mt-2 text-[14px] text-ink-300 leading-relaxed">
              No agent advances until a human signs off on its output. Approve in one click,
              annotate to refine, or kick the artifact back with a reason — D8X re-runs and updates lineage.
            </p>
            <ul className="mt-5 space-y-2.5 text-[13.5px] text-ink-200">
              <li className="flex items-start gap-2.5">
                <Check size={16} strokeWidth={2} className="text-flame mt-0.5 shrink-0"/>
                Slack & email approvals with deep links
              </li>
              <li className="flex items-start gap-2.5">
                <Check size={16} strokeWidth={2} className="text-flame mt-0.5 shrink-0"/>
                Diff against the previous run
              </li>
              <li className="flex items-start gap-2.5">
                <Check size={16} strokeWidth={2} className="text-flame mt-0.5 shrink-0"/>
                Full revision history, signed and timestamped
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}

function Gate() {
  // Approval gate iconography between agents — small bracket-with-checkmark
  return (
    <div className="hidden md:flex absolute top-[20px]" style={{ left: 'auto' }} aria-hidden></div>
  );
}

function GateMini() {
  return (
    <svg width="22" height="14" viewBox="0 0 28 14" fill="none">
      <path d="M3 1v12M25 1v12" stroke="rgba(255,255,255,.6)" strokeWidth="1.4" strokeLinecap="round"/>
      <path d="M9 7l3 3 7-7" stroke="#ff7a3a" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

// ── helpers ──
function SectionLabel({ num, title, eyebrow, lead }) {
  return (
    <div className="flex items-end justify-between gap-8 flex-wrap">
      <div className="max-w-[640px]">
        <div className="flex items-center gap-3 text-[11px] uppercase tracking-[0.22em] text-ink-300">
          <span className="num text-flame">{num}</span>
          <span className="w-8 h-px bg-white/20"/>
          <span>{eyebrow}</span>
        </div>
        <h2 className="display mt-4 text-[36px] sm:text-[44px] lg:text-[52px] font-semibold leading-[1.02] tracking-[-0.025em]">
          {title}
        </h2>
        {lead && <p className="mt-4 text-[16px] text-ink-300 max-w-[58ch] leading-relaxed">{lead}</p>}
      </div>
    </div>
  );
}

Object.assign(window, { Nav, Hero, Pipeline, SectionLabel });
