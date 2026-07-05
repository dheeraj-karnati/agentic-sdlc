// Lower-page sections: Conflict demo, How it works, Consulting, Trust, Pricing, FAQ, Footer

// ─────────────────────────────────────────── CONFLICT DEMO ───
const CONFLICTS = [
  {
    id: 'CONF-047', severity: 'high', title: 'Retry policy disagreement',
    summary: 'Three sources prescribe different maximum retry counts for the auth flow. The codebase and verbal kickoff agree; the signed BRD does not.',
    sources: [
      { kind:'BRD',   loc:'BRD_v3.pdf · §4.2 · L47',          quote:'"…shall enforce a maximum of 3 retry attempts before lockout."', value:'3', conflict:true },
      { kind:'CODE',  loc:'auth_service.py · L122',           quote:'MAX_RETRIES = 5  # tuned 2026-04-05',                              value:'5', conflict:false, agreed:true },
      { kind:'NOTES', loc:'kickoff_2026-04-02.txt · 23:14',   quote:'"…we landed on five — three was too aggressive on mobile…"',     value:'5', conflict:false, agreed:true },
    ],
    rec: 'Update BRD §4.2 to 5; circulate amendment to security review.',
    confidence: 94,
  },
  {
    id: 'CONF-051', severity: 'critical', title: 'PII handling contradiction',
    summary: 'Spec mandates field-level encryption for user PII; an architecture meeting waived it for the analytics path. No amendment exists.',
    sources: [
      { kind:'SPEC',   loc:'data_security_v2.md · §3.1',                    quote:'"All PII fields MUST be encrypted at rest with KMS-managed keys."',          value:'enc', conflict:true },
      { kind:'NOTES',  loc:'arch_review_2026-04-09.txt · 41:02',            quote:'"…analytics path can skip encryption for v1, we re-add in v2…"',          value:'plain', conflict:true },
      { kind:'CODE',   loc:'pipelines/events.ts · L88',                     quote:'enrichEvent(payload) // no encryption layer',                              value:'plain', conflict:true },
    ],
    rec: 'Block v1 release pending compliance review. Spec amendment required.',
    confidence: 99,
  },
  {
    id: 'CONF-063', severity: 'medium', title: 'Data retention window mismatch',
    summary: 'Privacy policy commits to 90 days; database TTL is set to 365.',
    sources: [
      { kind:'POLICY', loc:'privacy_policy.md · §7',                        quote:'"User events are retained for ninety (90) days."',                          value:'90d',  conflict:true },
      { kind:'CODE',   loc:'migrations/2026_04_001.sql · L14',              quote:"events.ttl = INTERVAL '365 days'",                                          value:'365d', conflict:true },
    ],
    rec: 'Align TTL with policy or amend policy with DPO sign-off.',
    confidence: 88,
  },
];

function ConflictDemo() {
  const [active, setActive] = useState(0);
  const c = CONFLICTS[active];

  return (
    <section id="conflicts" className="relative py-24 lg:py-32 border-t hairline bg-ink-900/40">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <SectionLabel num="02" eyebrow="Live D2 report" title="The wow moment, in one screen."
          lead="A real D2 Discover report. Each conflict cites the exact line, second, or commit it came from — with a confidence score and a recommended resolution your architects can ship in minutes." />

        <div className="mt-12 rounded-xl border hairline bg-ink-900 overflow-hidden shadow-card">
          {/* Window chrome */}
          <div className="flex items-center justify-between px-4 py-2.5 border-b hairline bg-ink-850">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-ink-700"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-ink-700"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-ink-700"></span>
              <span className="ml-3 text-[12px] num text-ink-300">d2_discover · run #4129 · acme-banking</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] num text-ink-400">
              <span>2.3s</span>
              <span className="hidden sm:inline">·</span>
              <span className="hidden sm:inline">12 sources scanned</span>
              <span className="hidden sm:inline">·</span>
              <span className="text-flame">7 conflicts</span>
            </div>
          </div>

          <div className="grid lg:grid-cols-12 min-h-[520px]">
            {/* Sidebar list */}
            <aside className="lg:col-span-4 border-b lg:border-b-0 lg:border-r hairline">
              <div className="px-5 pt-5 pb-3 flex items-center justify-between">
                <span className="text-[11px] uppercase tracking-[0.18em] text-ink-400">Findings</span>
                <span className="text-[11px] num text-ink-400">{CONFLICTS.length} of 7</span>
              </div>
              <ul>
                {CONFLICTS.map((cf, i) => (
                  <li key={cf.id}>
                    <button onClick={() => setActive(i)}
                      className={`w-full text-left px-5 py-4 border-l-2 transition flex flex-col gap-1.5 ${
                        i === active
                          ? 'border-flame bg-flame/5'
                          : 'border-transparent hover:bg-ink-850/60'
                      }`}>
                      <div className="flex items-center gap-2">
                        <SeverityDot severity={cf.severity}/>
                        <span className="num text-[11px] text-ink-400">{cf.id}</span>
                        <span className="num text-[10px] uppercase tracking-wider text-ink-300 ml-auto">{cf.severity}</span>
                      </div>
                      <div className={`text-[14px] leading-snug ${i === active ? 'text-ink-50' : 'text-ink-100'}`}>
                        {cf.title}
                      </div>
                    </button>
                  </li>
                ))}
                <li className="px-5 py-4 text-[12.5px] text-ink-400 italic border-l-2 border-transparent">
                  + 4 lower-priority findings
                </li>
              </ul>
            </aside>

            {/* Detail panel */}
            <div className="lg:col-span-8 p-6 lg:p-8">
              <div className="flex items-start justify-between gap-6 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em]">
                    <SeverityDot severity={c.severity}/>
                    <span className="text-flame num">{c.id}</span>
                    <span className="text-ink-400">·</span>
                    <span className="text-ink-300">{c.severity} severity</span>
                  </div>
                  <h3 className="display mt-2 text-[26px] font-semibold tracking-tight">{c.title}</h3>
                  <p className="mt-2 text-[14.5px] text-ink-300 max-w-[60ch] leading-relaxed">{c.summary}</p>
                </div>
                <div className="text-right">
                  <div className="text-[10.5px] uppercase tracking-[0.18em] text-ink-400">Confidence</div>
                  <div className="num text-[34px] font-semibold text-ink-50 leading-none mt-1">{c.confidence}<span className="text-[18px] text-ink-300">%</span></div>
                </div>
              </div>

              {/* Source rows */}
              <div className="mt-7 space-y-2.5">
                {c.sources.map((s, i) => (
                  <SourceRow key={i} {...s}/>
                ))}
              </div>

              {/* Recommendation */}
              <div className="mt-7 border-t hairline pt-5 flex flex-col sm:flex-row sm:items-center gap-4 sm:justify-between">
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded bg-flame/10 border border-flame/30 flex items-center justify-center text-flame shrink-0 mt-0.5">
                    <Workflow size={14} strokeWidth={1.8}/>
                  </div>
                  <div>
                    <div className="text-[10.5px] uppercase tracking-[0.18em] text-ink-400">Recommended resolution</div>
                    <div className="text-[14px] text-ink-100 mt-0.5">{c.rec}</div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button className="text-[12.5px] text-ink-200 hover:text-ink-50 px-3 py-2 rounded border hairline transition">Defer</button>
                  <button className="text-[12.5px] text-ink-200 hover:text-ink-50 px-3 py-2 rounded border hairline transition">Annotate</button>
                  <button className="text-[12.5px] font-medium text-ink-950 bg-flame hover:bg-flame-soft px-3 py-2 rounded inline-flex items-center gap-1.5 transition">
                    Resolve <ArrowRight size={13} strokeWidth={2.2}/>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function SeverityDot({ severity }) {
  const cls = severity === 'critical' ? 'bg-flame shadow-[0_0_8px_2px_rgba(255,122,58,.5)]' :
              severity === 'high' ? 'bg-flame' : 'bg-ink-300';
  return <span className={`inline-block w-1.5 h-1.5 rounded-full ${cls}`}></span>;
}

function SourceRow({ kind, loc, quote, value, conflict, agreed }) {
  return (
    <div className={`grid grid-cols-12 gap-3 items-start p-3.5 rounded-md border ${
      conflict ? 'border-flame/40 bg-flame/[0.04]' : 'hairline bg-ink-850/60'
    }`}>
      <div className="col-span-12 sm:col-span-2 flex items-center gap-2">
        <span className={`text-[10px] num uppercase tracking-[0.18em] px-1.5 py-0.5 rounded ${
          conflict ? 'text-flame bg-flame/10' : 'text-ink-300 bg-ink-800'
        }`}>{kind}</span>
        {agreed && (
          <span className="text-[10px] num uppercase tracking-[0.16em] text-moss inline-flex items-center gap-1">
            <Check size={11} strokeWidth={2.2}/> match
          </span>
        )}
      </div>
      <div className="col-span-12 sm:col-span-7">
        <div className="num text-[11px] text-ink-400">{loc}</div>
        <div className={`mt-1 font-mono text-[12.5px] leading-snug ${conflict ? 'text-ink-50' : 'text-ink-200'}`}>{quote}</div>
      </div>
      <div className="col-span-12 sm:col-span-3 flex sm:justify-end">
        <span className={`num text-[12.5px] px-2.5 py-1 rounded ${
          conflict ? 'bg-flame text-ink-950' : 'bg-ink-800 text-ink-100 border hairline'
        }`}>{value}</span>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────── HOW IT WORKS ───
function HowItWorks() {
  return (
    <section id="how" className="relative py-24 lg:py-32 border-t hairline">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <SectionLabel num="03" eyebrow="How it works" title="Three steps. Every handoff yours to approve."
          lead="D8X is opinionated about agents and uncompromising about humans. You stay in the loop at every gate."/>

        <div className="mt-14 grid lg:grid-cols-3 gap-5">
          <Step n="01" title="Connect your sources" body="Point D8X at the artifacts you already have — Jira, Confluence, GitHub, Notion, SharePoint, or just drag a folder in. We normalize them and keep line-level provenance.">
            <SourceLogos/>
          </Step>
          <Step n="02" title="Agents run with approval gates" body="D1 → D8 advance one stage at a time. Each agent ships an artifact; nothing moves to the next stage without your sign-off. Re-runs are diffed, not redone.">
            <AgentsRow/>
          </Step>
          <Step n="03" title="You review and approve" body="Approve from Slack, email, or the dashboard. Annotate to refine, kick back with a reason to re-run. The decision is signed and logged.">
            <ApproveCard/>
          </Step>
        </div>
      </div>
    </section>
  );
}

function Step({ n, title, body, children }) {
  return (
    <div className="bg-ink-850 border hairline rounded-lg p-6 flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <span className="num text-[11px] tracking-[0.22em] text-ink-400">STEP {n}</span>
        <span className="w-8 h-px bg-white/15"/>
      </div>
      <div>
        <h3 className="display text-[22px] font-semibold tracking-tight">{title}</h3>
        <p className="mt-2 text-[14px] text-ink-300 leading-relaxed">{body}</p>
      </div>
      <div className="mt-auto pt-2">
        {children}
      </div>
    </div>
  );
}

function SourceLogos() {
  const items = ['Jira','Confluence','GitHub','Notion','SharePoint','Loom','Slack','Drive','Figma','Drag & drop'];
  return (
    <div className="grid grid-cols-3 gap-1.5">
      {items.slice(0,9).map((s, i) => (
        <div key={s} className="aspect-[2/1] flex items-center justify-center text-[11px] text-ink-300 border hairline rounded bg-ink-900/60 hover:border-flame/50 hover:text-ink-100 transition">
          {s}
        </div>
      ))}
    </div>
  );
}

function AgentsRow() {
  return (
    <div className="relative">
      <div className="flex items-center gap-1">
        {AGENTS.map((a, i) => (
          <React.Fragment key={a.id}>
            <div className={`flex-1 aspect-square rounded flex items-center justify-center text-[10.5px] num font-medium border
              ${a.hero ? 'bg-flame text-ink-950 border-flame' : 'bg-ink-900 text-ink-200 hairline'}`}>
              {a.id}
            </div>
            {i < AGENTS.length - 1 && (
              <svg width="8" height="14" viewBox="0 0 8 14" className="shrink-0">
                <path d="M2 1v12M6 1v12" stroke="rgba(255,255,255,.35)" strokeWidth="1.2" strokeLinecap="round"/>
              </svg>
            )}
          </React.Fragment>
        ))}
      </div>
      <div className="mt-3 text-[10.5px] num uppercase tracking-[0.18em] text-ink-400 flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-flame animate-blink"></span> running · D2 awaiting approval
      </div>
    </div>
  );
}

function ApproveCard() {
  return (
    <div className="border hairline rounded-md bg-ink-900/80 p-3 text-[12.5px]">
      <div className="flex items-center gap-2">
        <span className="w-6 h-6 rounded-full bg-flame/15 border border-flame/40 inline-flex items-center justify-center text-flame">
          <Workflow size={12} strokeWidth={2}/>
        </span>
        <span className="text-ink-100 font-medium">D3 Design ready for review</span>
        <span className="ml-auto num text-[10.5px] text-ink-400">2m</span>
      </div>
      <div className="mt-2 text-ink-300">
        Architecture, schema, and API contracts generated. <span className="text-ink-100">12 entities</span>, <span className="text-ink-100">4 services</span>.
      </div>
      <div className="mt-3 flex items-center gap-1.5">
        <button className="text-[11.5px] font-medium text-ink-950 bg-flame px-2.5 py-1.5 rounded hover:bg-flame-soft">Approve</button>
        <button className="text-[11.5px] text-ink-200 border hairline px-2.5 py-1.5 rounded hover:bg-ink-800">Annotate</button>
        <button className="text-[11.5px] text-ink-300 hover:text-ink-100 px-2.5 py-1.5">Send back</button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────── CONSULTING ───
function Consulting() {
  const items = [
    { icon: Boxes,    title: 'Multi-tenant from day one', body: 'Logical isolation per client engagement. Onboard a new client without touching infra.' },
    { icon: Lock,     title: 'Audit trail on every decision', body: 'Every prompt, every approval, every conflict resolution — signed, timestamped, exportable.' },
    { icon: Sliders,  title: 'White-label ready', body: 'Your firm’s name on the dashboard. Your brand in the deliverables. Your CSAT ratings.' },
    { icon: Globe,    title: 'Plays nice with their stack', body: 'Jira, Confluence, ServiceNow, Azure DevOps, GitHub Enterprise, on-prem GitLab. We meet the client where they are.' },
  ];
  return (
    <section id="product" className="relative py-24 lg:py-32 border-t hairline bg-ink-900/40">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <SectionLabel num="04" eyebrow="Built for consulting firms" title="The platform your architects wish you bought."
          lead="D8X is shaped for mid-market firms (10–200 people) running enterprise client engagements where the client’s tools, not yours, are the constraint."/>
        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-px bg-white/5 border hairline rounded-lg overflow-hidden">
          {items.map(({ icon: Ic, title, body }) => (
            <div key={title} className="bg-ink-900 p-7 hover:bg-ink-850 transition">
              <Ic size={20} strokeWidth={1.6} className="text-flame"/>
              <h4 className="display mt-5 text-[18px] font-semibold tracking-tight leading-tight">{title}</h4>
              <p className="mt-2 text-[13.5px] text-ink-300 leading-relaxed">{body}</p>
            </div>
          ))}
        </div>

        {/* Numbers strip */}
        <div className="mt-10 grid sm:grid-cols-3 gap-px bg-white/5 border hairline rounded-lg overflow-hidden">
          <BigStat n="40h" label="Architect hours reclaimed per week" sub="Avg. across pilots, Q1 2026"/>
          <BigStat n="11×" label="Faster requirements to PR" sub="Median engagement, n=18"/>
          <BigStat n="2-3×" label="More billable engagements" sub="Same headcount, same quarter"/>
        </div>
      </div>
    </section>
  );
}

function BigStat({ n, label, sub }) {
  return (
    <div className="bg-ink-900 p-7">
      <div className="num text-[52px] font-semibold leading-none text-ink-50 tracking-tight">{n}</div>
      <div className="mt-3 text-[13.5px] text-ink-100">{label}</div>
      <div className="mt-1 text-[11.5px] num text-ink-400">{sub}</div>
    </div>
  );
}

// ─────────────────────────────────────────── TRUST ───
function Trust() {
  return (
    <section className="relative py-24 lg:py-32 border-t hairline">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <SectionLabel num="05" eyebrow="Trust & observability" title="Every decision, explainable."
          lead="If you can’t answer ‘why did the agent do that?’ in court — or in front of the client’s CTO — you can’t use the platform. So we built D8X assuming you have to."/>

        <div className="mt-12 grid lg:grid-cols-12 gap-6">
          {/* Left: lineage panel mock */}
          <div className="lg:col-span-7 bg-ink-850 border hairline rounded-lg overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b hairline">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-ink-400">
                <Activity size={12} strokeWidth={2}/> Lineage · req-2147 → PR #482
              </div>
              <span className="num text-[10.5px] text-ink-400">7 hops · 12s total</span>
            </div>
            <div className="p-5 space-y-3 font-mono text-[12.5px]">
              {[
                { tag:'D1', t:'parsed', what:'BRD_v3.pdf §4.2 → req-2147', conf:'1.00' },
                { tag:'D2', t:'discovered', what:'flagged CONF-047 (retry policy)', conf:'0.94', flame:true },
                { tag:'D2', t:'resolved', what:'human approved: MAX_RETRIES = 5', conf:'—' },
                { tag:'D3', t:'designed', what:'AuthService.retry contract emitted', conf:'0.97' },
                { tag:'D5', t:'planned', what:'story-318 acceptance criteria', conf:'0.92' },
                { tag:'D6', t:'built', what:'PR #482 · auth_service.py:122', conf:'0.96' },
                { tag:'D7', t:'tested', what:'12/12 passed · sec scan clean', conf:'1.00' },
              ].map((row, i) => (
                <div key={i} className="grid grid-cols-12 gap-3 items-center">
                  <span className={`col-span-1 text-[10.5px] num font-semibold ${row.flame ? 'text-flame' : 'text-ink-300'}`}>{row.tag}</span>
                  <span className="col-span-2 text-[10.5px] uppercase tracking-wider text-ink-400">{row.t}</span>
                  <span className={`col-span-7 truncate ${row.flame ? 'text-flame' : 'text-ink-100'}`}>{row.what}</span>
                  <span className="col-span-2 text-right num text-[11px] text-ink-300">{row.conf}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Right: trust principles */}
          <div className="lg:col-span-5 space-y-3">
            <TrustItem icon={Eye} title="Every LLM call traced" body="Prompt, context window, output, tokens, latency. Filter by agent, by run, by client engagement."/>
            <TrustItem icon={Activity} title="Confidence scores you can act on" body="Calibrated against ground truth. Conflicts under 90% surface for human review by default."/>
            <TrustItem icon={Layers} title="Full lineage, requirement → code" body="Click any line in a PR; trace it back to the BRD page that produced it. Or the meeting that overruled it."/>
            <TrustItem icon={Shield} title="SOC 2 Type II · ISO 27001 in flight" body="No training on your data. EU residency available. On-prem deployment for the truly paranoid."/>
          </div>
        </div>
      </div>
    </section>
  );
}

function TrustItem({ icon: Ic, title, body }) {
  return (
    <div className="bg-ink-900 border hairline rounded-lg p-5 hover:border-white/15 transition">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded bg-ink-850 border hairline-strong flex items-center justify-center text-flame shrink-0">
          <Ic size={16} strokeWidth={1.7}/>
        </div>
        <div>
          <div className="text-[14.5px] font-medium text-ink-50">{title}</div>
          <div className="mt-1 text-[13px] text-ink-300 leading-relaxed">{body}</div>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────── PRICING ───
const PLANS = [
  {
    name: 'Pilot',
    scope: 'Per engagement',
    sub: 'Run D8X on one client engagement to prove the value before you commit firm-wide.',
    scale: 1,
    cadence: 'engagement-scoped',
    features: ['Up to 2 architects', '1 active project', 'D1–D5 agents', 'Email approvals', 'Standard support'],
    cta: 'Start a pilot',
  },
  {
    name: 'Firm',
    scope: 'Per firm, monthly',
    sub: 'For mid-market consultancies running concurrent engagements across the practice.',
    scale: 2,
    cadence: 'firm-wide subscription',
    recommended: true,
    features: ['Up to 10 seats', 'Unlimited projects', 'All 8 agents', 'Slack & email approvals', 'White-label dashboard', 'Audit log export', 'Priority support'],
    cta: 'Talk to sales',
  },
  {
    name: 'Scale',
    scope: 'Custom',
    sub: 'For larger firms, regulated industries, or anyone who needs the platform behind their own VPC.',
    scale: 3,
    cadence: 'enterprise agreement',
    features: ['Unlimited seats', 'On-prem / VPC option', 'SAML SSO + SCIM', 'Custom agent fine-tuning', 'Dedicated CSM + SLA', '99.9% uptime'],
    cta: 'Contact us',
  },
];

function Pricing() {
  return (
    <section id="pricing" className="relative py-24 lg:py-32 border-t hairline bg-ink-900/40">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <SectionLabel num="06" eyebrow="Pricing" title="Three tiers. Quoted to your engagement."
          lead="Pricing scales with seats and concurrent projects, not with token usage. We share an exact number once we understand your engagement shape — usually within a business day."/>

        <div className="mt-12 grid lg:grid-cols-3 gap-5">
          {PLANS.map(p => (
            <div key={p.name}
              className={`relative rounded-lg p-7 border flex flex-col ${
                p.recommended
                  ? 'bg-ink-850 border-flame/50 shadow-flame'
                  : 'bg-ink-900 hairline'
              }`}>
              {p.recommended && (
                <div className="absolute -top-3 left-7 inline-flex items-center gap-1.5 text-[10.5px] num uppercase tracking-[0.18em] bg-flame text-ink-950 px-2 py-1 rounded">
                  Recommended
                </div>
              )}

              {/* Header */}
              <div className="flex items-start justify-between gap-3">
                <h3 className="display text-[24px] font-semibold tracking-tight">{p.name}</h3>
                <ScaleDots scale={p.scale} flame={p.recommended}/>
              </div>

              {/* Scope (replaces giant $) */}
              <div className="mt-5 pb-5 border-b hairline">
                <div className="num text-[10.5px] uppercase tracking-[0.18em] text-ink-400">Pricing model</div>
                <div className={`mt-1.5 display text-[22px] leading-tight font-semibold tracking-tight ${p.recommended ? 'text-ink-50' : 'text-ink-100'}`}>
                  {p.scope}
                </div>
                <div className="mt-1 text-[11.5px] num text-ink-400 lowercase tracking-wide">{p.cadence}</div>
              </div>

              <p className="mt-5 text-[13.5px] text-ink-300 leading-relaxed">{p.sub}</p>

              <ul className="mt-5 space-y-2.5 text-[13.5px]">
                {p.features.map(f => (
                  <li key={f} className="flex items-start gap-2.5 text-ink-100">
                    <Check size={15} strokeWidth={2} className={`${p.recommended ? 'text-flame' : 'text-ink-300'} mt-0.5 shrink-0`}/>
                    {f}
                  </li>
                ))}
              </ul>

              <a href="#demo" className={`mt-7 inline-flex items-center justify-center gap-2 text-[14px] font-medium px-4 py-3 rounded transition ${
                p.recommended
                  ? 'bg-flame text-ink-950 hover:bg-flame-soft'
                  : 'border hairline-strong text-ink-100 hover:bg-ink-850'
              }`}>
                {p.cta} <ArrowRight size={14} strokeWidth={2.2}/>
              </a>
            </div>
          ))}
        </div>

        {/* Trust strip under the cards */}
        <div className="mt-8 grid sm:grid-cols-3 gap-px bg-white/5 border hairline rounded-lg overflow-hidden">
          <PricingNote icon={Zap}    title="No per-token surprises"   body="LLM compute is included on managed providers. Annual commits unlock 2 months free."/>
          <PricingNote icon={Workflow} title="Quote within 1 business day" body="Tell us seat count and active engagements; we send a fixed price the next morning."/>
          <PricingNote icon={Shield} title="Procurement-friendly"     body="MSAs, DPAs, security reviews, and SOC 2 reports ready on request."/>
        </div>
      </div>
    </section>
  );
}

function ScaleDots({ scale, flame }) {
  return (
    <div className="flex items-center gap-1 pt-2" aria-label={`Tier ${scale} of 3`}>
      {[1,2,3].map(i => (
        <span key={i}
          className={`w-2 h-2 rounded-full transition ${
            i <= scale
              ? (flame ? 'bg-flame' : 'bg-ink-100')
              : 'bg-ink-700'
          }`} />
      ))}
    </div>
  );
}

function PricingNote({ icon: Ic, title, body }) {
  return (
    <div className="bg-ink-900 p-5 flex items-start gap-3">
      <div className="w-8 h-8 rounded bg-ink-850 border hairline-strong flex items-center justify-center text-flame shrink-0">
        <Ic size={14} strokeWidth={1.8}/>
      </div>
      <div>
        <div className="text-[13px] font-medium text-ink-50">{title}</div>
        <div className="mt-0.5 text-[12px] text-ink-300 leading-relaxed">{body}</div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────── FAQ ───
const FAQS = [
  { q: 'How is this different from Cursor or Devin?',
    a: 'Cursor and Devin are coding copilots — they start where the requirements end. D8X starts where the BRD lands in your inbox. Our value is the four agents before D6 Build (Ingest, Discover, Design, Prototype), and specifically the patented cross-source conflict detection in D2.' },
  { q: 'How does conflict detection actually work?',
    a: 'Each source is parsed into a structured representation with line-level provenance. Entities, rules, and constraints get resolved against a shared ontology, then cross-referenced. We surface direct contradictions, semantic drift, and ambiguous handoffs — each scored and traced back to the exact span that produced it.' },
  { q: 'Do you train on our data or our clients’ data?',
    a: 'No. Tenant data is never used to train base models or shared across customers. Inference happens against managed model endpoints with zero-retention agreements. On-prem deployment removes the question entirely.' },
  { q: 'What integrations do you support?',
    a: 'Jira, Confluence, GitHub (Cloud + Enterprise), GitLab, Azure DevOps, Notion, SharePoint, Slack, Loom, Drive, Figma, plus drag-and-drop for everything else. Webhooks and a typed API for anything custom.' },
  { q: 'Can we run D8X on-premises?',
    a: 'Yes — Scale plan. We ship a Kubernetes Helm chart with bring-your-own model endpoints (Anthropic, OpenAI, Azure OpenAI, Bedrock, or self-hosted). Air-gapped deployments are available with a separate engagement.' },
  { q: 'What about security and compliance?',
    a: 'SOC 2 Type II audited. ISO 27001 in progress. SAML SSO and SCIM on Scale. EU data residency available. Every approval and agent decision is signed, hashed, and exportable for client audit.' },
];

function FAQ() {
  const [open, setOpen] = useState(0);
  return (
    <section id="faq" className="relative py-24 lg:py-32 border-t hairline">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-4">
            <SectionLabel num="07" eyebrow="FAQ" title="Questions, answered."
              lead="Couldn’t find yours? hello@d8x.com — a human replies."/>
          </div>
          <div className="lg:col-span-8">
            <div className="border-t hairline">
              {FAQS.map((f, i) => (
                <div key={i} className="border-b hairline">
                  <button onClick={() => setOpen(open === i ? -1 : i)}
                    className="w-full text-left flex items-center justify-between gap-6 py-5 group">
                    <span className={`text-[16px] sm:text-[17px] font-medium transition ${open === i ? 'text-ink-50' : 'text-ink-100 group-hover:text-ink-50'}`}>
                      {f.q}
                    </span>
                    <span className={`shrink-0 w-7 h-7 rounded-full border hairline-strong flex items-center justify-center transition ${open === i ? 'bg-flame text-ink-950 border-flame' : 'text-ink-200'}`}>
                      {open === i ? <Minus size={13} strokeWidth={2.2}/> : <Plus size={13} strokeWidth={2.2}/>}
                    </span>
                  </button>
                  <div className={`overflow-hidden transition-all duration-300 ${open === i ? 'max-h-[400px] opacity-100' : 'max-h-0 opacity-0'}`}>
                    <p className="pb-6 pr-14 text-[14.5px] text-ink-300 leading-relaxed">{f.a}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

// ─────────────────────────────────────────── CTA + FOOTER ───
function FinalCTA() {
  return (
    <section id="demo" className="relative py-24 lg:py-32 border-t hairline overflow-hidden">
      <div className="absolute inset-0 bg-grid opacity-50 [mask-image:radial-gradient(ellipse_at_center,black_30%,transparent_70%)]" />
      <div className="relative max-w-[1280px] mx-auto px-6 lg:px-8 text-center">
        <h2 className="display text-[44px] sm:text-[60px] lg:text-[76px] font-semibold leading-[0.98] tracking-[-0.03em] max-w-[18ch] mx-auto">
          Ship what the docs <span className="text-flame">actually say.</span>
        </h2>
        <p className="mt-6 text-[16px] text-ink-300 max-w-[52ch] mx-auto leading-relaxed">
          Bring your messiest engagement. We&apos;ll run D2 Discover live and walk you through every conflict it surfaces.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-3">
          <a href="#" className="inline-flex items-center gap-2 bg-flame text-ink-950 px-6 py-3.5 rounded font-medium text-[15px] hover:bg-flame-soft transition">
            Book a 30-minute demo <ArrowRight size={16} strokeWidth={2.2}/>
          </a>
          <a href="#" className="inline-flex items-center gap-2 border hairline-strong text-ink-100 px-6 py-3.5 rounded font-medium text-[15px] hover:bg-ink-850 transition">
            See it on your docs <ArrowUpRight size={16} strokeWidth={2}/>
          </a>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  const cols = [
    { h:'Product', items:['Overview','Agents','Pricing','Changelog','Status','Roadmap'] },
    { h:'Resources', items:['Docs','API','Security','Compliance','Customers','Blog'] },
    { h:'Company', items:['About','Careers','Press','Partners','Contact'] },
    { h:'Legal', items:['Terms','Privacy','DPA','Subprocessors','SOC 2 report'] },
  ];
  return (
    <footer className="relative border-t hairline pt-16 pb-10 bg-ink-950">
      <div className="max-w-[1280px] mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-12 gap-10">
          <div className="lg:col-span-4">
            <div className="flex items-center gap-2">
              <Logo/>
              <span className="display text-[20px] font-semibold">D8X</span>
            </div>
            <p className="mt-4 text-[13.5px] text-ink-300 leading-relaxed max-w-[40ch]">
              Agentic SDLC for consulting firms. From requirements to deployed code — with a human at every gate.
            </p>
            <div className="mt-6 flex items-center gap-2 text-[11px] num uppercase tracking-[0.18em] text-ink-400">
              <span className="w-1.5 h-1.5 rounded-full bg-moss inline-block animate-blink"></span>
              All systems operational
            </div>
          </div>
          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-8">
            {cols.map(c => (
              <div key={c.h}>
                <div className="text-[11px] num uppercase tracking-[0.18em] text-ink-400">{c.h}</div>
                <ul className="mt-4 space-y-2.5">
                  {c.items.map(i => (
                    <li key={i}><a href="#" className="text-[13.5px] text-ink-200 hover:text-ink-50 transition">{i}</a></li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-14 pt-6 border-t hairline flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-[12px] text-ink-400">
          <div>© 2026 D8X, Inc. All rights reserved.</div>
          <div className="flex items-center gap-2 num uppercase tracking-[0.16em]">
            <span className="w-1 h-1 rounded-full bg-flame inline-block"></span>
            Patent pending — Cross-source conflict detection
          </div>
        </div>
      </div>
    </footer>
  );
}

// Small monogram used by Logo() in this file too — but we reuse the one from sections.jsx
function Logo() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="1.5" y="1.5" width="21" height="21" rx="4" stroke="currentColor" strokeOpacity=".5" strokeWidth="1.4"/>
      <circle cx="9.5" cy="9.5" r="2.4" stroke="#ff7a3a" strokeWidth="1.6"/>
      <circle cx="14.5" cy="14.5" r="2.4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M14.5 9.5h2.5M9.5 14.5H7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

Object.assign(window, { ConflictDemo, HowItWorks, Consulting, Trust, Pricing, FAQ, FinalCTA, Footer });
