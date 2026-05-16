"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ChevronRight,
  ChevronDown,
  Plus,
  Minus,
  AlertTriangle,
  FileText,
  Search,
  Shapes,
  Zap,
  GitPullRequest,
  Shield,
  Rocket,
  Eye,
  Layers,
  ArrowUpRight,
  Workflow,
  X,
  Sliders,
  Flame,
} from "lucide-react";

/* ───────────────────────────────────────────────
   Logo
   ─────────────────────────────────────────────── */

function D8XLogo() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden>
      <rect x="1.5" y="1.5" width="21" height="21" rx="4" stroke="currentColor" strokeOpacity=".5" strokeWidth="1.4"/>
      <circle cx="9.5" cy="9.5" r="2.4" stroke="#ff7a3a" strokeWidth="1.6"/>
      <circle cx="14.5" cy="14.5" r="2.4" stroke="currentColor" strokeWidth="1.6"/>
      <path d="M14.5 9.5h2.5M9.5 14.5H7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
    </svg>
  );
}

/* ───────────────────────────────────────────────
   Data Constants
   ─────────────────────────────────────────────── */

const AGENTS = [
  { id: "D1", name: "Ingest", tag: "parse", icon: FileText, blurb: "Parses any input format", detail: "Connect any source — PDFs, DOCX, Markdown, source code, screenshots, meeting recordings. D1 normalizes everything into structured documents with line-level provenance.", tags: ["PDF", "DOCX", "ZIP", "Code", "Audio"] },
  { id: "D2", name: "Discover", tag: "reconcile", icon: Search, blurb: "Extracts requirements & finds CONFLICTS", detail: "The core engine. D2 extracts requirements, business rules, and entities — then cross-references them across every source. It surfaces contradictions, semantic mismatches, and security vulnerabilities.", tags: ["Conflicts", "Entities", "Rules", "Vulnerabilities"], hero: true },
  { id: "D3", name: "Design", tag: "architect", icon: Shapes, blurb: "Architecture, schema, contracts", detail: "Generates system architecture, database schema, API contracts, auth model — all justified by the actual requirements, not hardcoded assumptions.", tags: ["ADRs", "Schema", "API", "Auth"] },
  { id: "D4", name: "Prototype", tag: "demo", icon: Zap, blurb: "Interactive demo for stakeholders", detail: "Spins up a clickable prototype for stakeholder review. Feedback flows back as new constraints.", tags: ["Clickable", "Versioned"] },
  { id: "D5", name: "Plan", tag: "sequence", icon: Layers, blurb: "Epics & sequenced stories", detail: "Breaks scope into epics, sequences user stories with dependency-aware ordering and acceptance criteria.", tags: ["Epics", "Stories", "Estimates"] },
  { id: "D6", name: "Build", tag: "code", icon: GitPullRequest, blurb: "Code generation, PRs", detail: "Writes feature branches and opens pull requests. Every PR cites the requirement IDs it implements.", tags: ["PRs", "Branches"] },
  { id: "D7", name: "Test", tag: "verify", icon: Shield, blurb: "QA, security, coverage", detail: "Unit, integration, E2E tests plus security and accessibility scans.", tags: ["Unit", "E2E", "SAST"] },
  { id: "D8", name: "Ship", tag: "deploy", icon: Rocket, blurb: "Deploy and monitor", detail: "Promotes through environments with health gates. Production telemetry loops back to D2.", tags: ["Deploy", "Telemetry"] },
];

const CONFLICTS = [
  {
    id: "CONF-047", severity: "high" as const, title: "Retry policy disagreement",
    summary: "Three sources prescribe different maximum retry counts for the auth flow.",
    sources: [
      { kind: "BRD", loc: "BRD_v3.pdf \u00b7 \u00a74.2 \u00b7 L47", quote: "\u201c\u2026shall enforce a maximum of 3 retry attempts before lockout.\u201d", value: "3", conflict: true },
      { kind: "CODE", loc: "auth_service.py \u00b7 L122", quote: "MAX_RETRIES = 5  # tuned 2026-04-05", value: "5", conflict: false },
      { kind: "NOTES", loc: "kickoff_2026-04-02.txt \u00b7 23:14", quote: "\u201c\u2026we landed on five \u2014 three was too aggressive on mobile\u2026\u201d", value: "5", conflict: false },
    ],
    rec: "Update BRD \u00a74.2 to 5; circulate amendment to security review.", confidence: 94,
  },
  {
    id: "CONF-051", severity: "critical" as const, title: "PII handling contradiction",
    summary: "Spec mandates field-level encryption for user PII; an architecture meeting waived it for the analytics path.",
    sources: [
      { kind: "SPEC", loc: "data_security_v2.md \u00b7 \u00a73.1", quote: "\u201cAll PII fields MUST be encrypted at rest with KMS-managed keys.\u201d", value: "enc", conflict: true },
      { kind: "NOTES", loc: "arch_review_2026-04-09.txt \u00b7 41:02", quote: "\u201c\u2026analytics path can skip encryption for v1, we re-add in v2\u2026\u201d", value: "plain", conflict: true },
      { kind: "CODE", loc: "pipelines/events.ts \u00b7 L88", quote: "enrichEvent(payload) // no encryption layer", value: "plain", conflict: true },
    ],
    rec: "Block v1 release pending compliance review.", confidence: 99,
  },
  {
    id: "CONF-063", severity: "medium" as const, title: "Data retention window mismatch",
    summary: "Privacy policy commits to 90 days; database TTL is set to 365.",
    sources: [
      { kind: "POLICY", loc: "privacy_policy.md \u00b7 \u00a77", quote: "\u201cUser events are retained for ninety (90) days.\u201d", value: "90d", conflict: true },
      { kind: "CODE", loc: "migrations/2026_04_001.sql \u00b7 L14", quote: "events.ttl = INTERVAL '365 days'", value: "365d", conflict: true },
    ],
    rec: "Align TTL with policy or amend policy with DPO sign-off.", confidence: 88,
  },
];

const STEPS = [
  { step: "01", title: "Connect your sources", desc: "Drop in BRDs, source code, meeting recordings, Figma files, database schemas. The Ingest agent parses everything.", icon: FileText },
  { step: "02", title: "Agents run with gates", desc: "Eight specialized agents work in sequence. Between every phase, you review and approve before the next agent starts.", icon: Workflow },
  { step: "03", title: "You review and approve", desc: "Human-in-the-loop at every stage. Approve, reject, or request changes. Full audit trail of every decision.", icon: Eye },
];

const TECH_STACK = [
  { name: "Python 3.12 + FastAPI", desc: "Async backend" },
  { name: "LangGraph", desc: "Agent orchestration" },
  { name: "PostgreSQL + pgvector", desc: "Vector search" },
  { name: "Next.js 14 + Tailwind", desc: "Dashboard" },
  { name: "Google Gemini 2.5 Flash", desc: "Primary LLM" },
  { name: "unstructured.io", desc: "Document parsing" },
];

const FAQS = [
  { q: "What is D8X?", a: "D8X is a multi-agent AI platform that automates the full SDLC \u2014 from requirements analysis through deployment. Its core innovation is cross-source conflict detection: automatically finding contradictions between BRDs, source code, and meeting notes." },
  { q: "How does conflict detection work?", a: "Each source is parsed into structured elements with provenance. Business rules, entities, and constraints are extracted per-document, then cross-referenced. D8X surfaces direct contradictions, semantic drift, and security vulnerabilities \u2014 each scored and traced back to the exact line or timestamp." },
  { q: "What LLMs does it support?", a: "Google Gemini 2.5 Flash (primary), Groq Llama 3.3 70B, Cerebras, OpenRouter, and Ollama for local inference. The provider chain falls back automatically if one fails." },
  { q: "What file types can it process?", a: "PDF, DOCX, Markdown, source code (Java, COBOL, PL/SQL, Progress 4GL, Python, C#, and more), SQL schemas, ZIP archives with automatic extraction, and plain text. Enterprise codebases with 2000+ files are supported via smart classification and tiered analysis." },
  { q: "How do I get access?", a: "D8X is currently in private beta. Book a demo and we\u2019ll walk you through the platform live with your own documents." },
  { q: "Is my data secure?", a: "Yes. Your data is never used for training. Tenant isolation is enforced at every layer. Every agent decision, approval, and prompt is signed and logged for audit." },
];

/* ───────────────────────────────────────────────
   Intersection Observer Hook
   ─────────────────────────────────────────────── */

function useOnScreen(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setVisible(true); },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

/* ───────────────────────────────────────────────
   ConflictHeroVisual — SVG lines + 3 doc cards
   converging to contradiction card
   ─────────────────────────────────────────────── */

function ConflictHeroVisual() {
  return (
    <div className="relative w-full max-w-md mx-auto" style={{ height: 380 }}>
      {/* Document cards at top with rotation */}
      {/* Doc A - BRD */}
      <div
        className="absolute w-40 p-3 bg-ink-800 border border-white/[0.06] rounded-lg shadow-card-glow"
        style={{ top: 0, left: 0, transform: "rotate(-6deg)" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <FileText className="w-3.5 h-3.5 text-ink-300" />
          <span className="text-[10px] text-ink-300 font-mono">BRD_v3.pdf</span>
        </div>
        <p className="text-[11px] text-ink-200 leading-relaxed">
          &quot;...shall enforce a maximum of <span className="text-flame font-medium">3 retry</span> attempts...&quot;
        </p>
      </div>

      {/* Doc B - code */}
      <div
        className="absolute w-40 p-3 bg-ink-800 border border-white/[0.06] rounded-lg shadow-card-glow"
        style={{ top: 0, left: "50%", transform: "translateX(-50%) rotate(0deg)" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <FileText className="w-3.5 h-3.5 text-ink-300" />
          <span className="text-[10px] text-ink-300 font-mono">auth_service.py</span>
        </div>
        <p className="text-[11px] text-ink-200 leading-relaxed font-mono">
          MAX_RETRIES = <span className="text-flame font-medium">5</span>
        </p>
      </div>

      {/* Doc C - transcript */}
      <div
        className="absolute w-40 p-3 bg-ink-800 border border-white/[0.06] rounded-lg shadow-card-glow"
        style={{ top: 0, right: 0, transform: "rotate(6deg)" }}
      >
        <div className="flex items-center gap-2 mb-2">
          <FileText className="w-3.5 h-3.5 text-ink-300" />
          <span className="text-[10px] text-ink-300 font-mono truncate">kickoff transcript</span>
        </div>
        <p className="text-[11px] text-ink-200 leading-relaxed">
          &quot;...we landed on <span className="text-flame font-medium">five</span>...&quot;
        </p>
      </div>

      {/* SVG connecting lines */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 1 }}>
        {/* Line from doc A to contradiction card */}
        <line x1="80" y1="100" x2="200" y2="210" stroke="rgba(255,122,58,0.25)" strokeWidth="1" strokeDasharray="4 4" />
        {/* Line from doc B to contradiction card */}
        <line x1="200" y1="100" x2="200" y2="210" stroke="rgba(255,122,58,0.25)" strokeWidth="1" strokeDasharray="4 4" />
        {/* Line from doc C to contradiction card */}
        <line x1="320" y1="100" x2="200" y2="210" stroke="rgba(255,122,58,0.25)" strokeWidth="1" strokeDasharray="4 4" />
      </svg>

      {/* Contradiction card */}
      <div
        className="absolute left-1/2 -translate-x-1/2 w-64 p-4 bg-ink-850 border border-flame/30 rounded-lg shadow-flame"
        style={{ top: 210, zIndex: 2 }}
      >
        <div className="flex items-center gap-2 mb-1">
          <Flame className="w-4 h-4 text-flame" />
          <span className="text-[10px] font-mono text-ink-400">CONF #047</span>
        </div>
        <h4 className="text-xs font-semibold text-flame mb-1">Contradiction detected</h4>
        <p className="text-[11px] text-ink-300 leading-relaxed mb-3">
          Three sources prescribe different retry counts for auth flow.
        </p>

        {/* Source summary rows */}
        <div className="space-y-1.5 mb-3">
          {[
            { kind: "BRD", value: "3" },
            { kind: "CODE", value: "5" },
            { kind: "NOTES", value: "5" },
          ].map((s) => (
            <div key={s.kind} className="flex items-center justify-between">
              <span className="text-[10px] font-mono text-ink-400">{s.kind}</span>
              <span className={`text-[10px] font-mono font-medium ${s.value === "3" ? "text-flame" : "text-ink-200"}`}>{s.value}</span>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] text-ink-400">Confidence</span>
            <span className="num text-sm font-bold text-flame">94%</span>
          </div>
          <span className="text-[10px] text-flame font-medium cursor-pointer hover:underline">Resolve &rarr;</span>
        </div>
      </div>
    </div>
  );
}

/* ───────────────────────────────────────────────
   Nav
   ─────────────────────────────────────────────── */

function Nav() {
  const [scrolled, setScrolled] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", h, { passive: true });
    return () => window.removeEventListener("scroll", h);
  }, []);

  const links = [
    { label: "Agents", href: "#agents" },
    { label: "How it works", href: "#how" },
    { label: "FAQ", href: "#faq" },
  ];

  return (
    <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled ? "bg-ink-950/90 backdrop-blur-xl border-b hairline" : ""}`}>
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2.5 group">
          <D8XLogo />
          <span className="display text-[19px] font-semibold tracking-tight text-white">D8X</span>
        </a>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-8 text-sm text-ink-300">
          {links.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="hover:text-white transition-colors"
            >
              {l.label}
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-4">
          <Link
            href="/projects/new"
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-flame text-white rounded-lg hover:bg-flame-deep transition-colors shadow-flame"
          >
            Try Demo
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mobile toggle */}
        <button className="md:hidden text-ink-300" onClick={() => setMobileOpen(!mobileOpen)}>
          {mobileOpen ? <X className="w-5 h-5" /> : <Sliders className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile menu */}
      {mobileOpen && (
        <div className="md:hidden bg-ink-950/95 backdrop-blur-xl border-t hairline px-6 py-4 space-y-3">
          {links.map((l) => (
            <a
              key={l.label}
              href={l.href}
              className="block text-sm text-ink-300 hover:text-white"
              onClick={() => setMobileOpen(false)}
            >
              {l.label}
            </a>
          ))}
          <Link href="/projects/new" className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium bg-flame text-white rounded-lg">
            Try Demo <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}
    </nav>
  );
}

/* ───────────────────────────────────────────────
   Hero
   ─────────────────────────────────────────────── */

function Hero() {
  return (
    <section id="hero" className="relative min-h-screen flex items-center overflow-hidden bg-ink-950">
      {/* Subtle grid background */}
      <div className="absolute inset-0 bg-grid opacity-40" />
      {/* Glow */}
      <div className="absolute top-1/3 left-1/4 w-[500px] h-[500px] bg-flame/[0.04] rounded-full blur-[160px]" />

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-32 grid lg:grid-cols-2 gap-16 items-center">
        {/* Left */}
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-flame/20 bg-flame/[0.06] text-flame text-xs font-medium mb-8">
            <span className="w-1.5 h-1.5 rounded-full bg-flame animate-ping" />
            Patent Pending
          </div>

          <h1 className="display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold tracking-tight leading-[1.05] text-white">
            Catch the contradictions{" "}
            <span className="text-ink-400">your team cannot.</span>
          </h1>

          <p className="mt-6 text-lg text-ink-300 max-w-lg leading-relaxed">
            D8X is an agentic SDLC platform that automatically finds contradictions across your BRDs, source code, and meeting notes — before they become production incidents.
          </p>

          <div className="mt-8 flex flex-col sm:flex-row gap-3">
            <Link
              href="/projects/new"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium bg-flame text-white rounded-lg hover:bg-flame-deep transition-colors shadow-flame"
            >
              Try the Demo
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              href="/book-demo"
              className="inline-flex items-center justify-center gap-2 px-6 py-3 text-sm font-medium border border-white/10 text-ink-200 rounded-lg hover:bg-white/[0.04] transition-colors"
            >
              Book a Demo
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {/* Stats */}
          <div className="mt-12 flex gap-10">
            {[
              { value: "8", label: "specialized agents" },
              { value: "6", label: "enterprise languages" },
              { value: "100%", label: "traceable" },
            ].map((s) => (
              <div key={s.label}>
                <div className="num text-2xl font-bold text-white">{s.value}</div>
                <div className="text-xs text-ink-400 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Right — ConflictHeroVisual */}
        <div className="hidden lg:block">
          <ConflictHeroVisual />
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Pipeline — "The eight agents"
   ─────────────────────────────────────────────── */

function Pipeline() {
  const { ref, visible } = useOnScreen();
  const [active, setActive] = useState(1); // D2 default (hero agent)

  const agent = AGENTS[active];
  const Icon = agent.icon;

  return (
    <section id="agents" className="py-28 bg-ink-950 relative" ref={ref}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-xs font-mono uppercase tracking-widest text-flame mb-3">Pipeline</p>
          <h2 className="display text-3xl md:text-5xl font-bold tracking-tight text-white">
            The eight agents
          </h2>
          <p className="mt-4 text-ink-300 max-w-2xl mx-auto">
            Each agent is a specialist. Connected by a shared Business Context Store so every decision builds on the last.
          </p>
        </div>

        {/* Agent nodes row */}
        <div className="relative">
          {/* Connection line */}
          <div className="hidden lg:block absolute top-[37px] left-[4%] right-[4%] h-px bg-ink-700" />

          {/* Animated flow dots */}
          <div className="hidden lg:block absolute top-[36px] left-[4%] right-[4%] h-[3px] overflow-hidden">
            {[0, 1, 2, 3].map((i) => (
              <div
                key={i}
                className="absolute w-8 h-px bg-gradient-to-r from-transparent via-flame to-transparent animate-flow"
                style={{ animationDelay: `${i * 0.8}s` }}
              />
            ))}
          </div>

          {/* Approval gate SVG icons between nodes (desktop only) */}
          <div className="hidden lg:flex absolute top-[30px] left-[4%] right-[4%] justify-around pointer-events-none" style={{ paddingLeft: "6%", paddingRight: "6%" }}>
            {[0, 1, 2, 3, 4, 5, 6].map((i) => (
              <svg key={i} className="w-3.5 h-3.5 text-ink-600" viewBox="0 0 16 16" fill="none">
                <path d="M8 1L10 6H14L11 9L12 14L8 11L4 14L5 9L2 6H6L8 1Z" stroke="currentColor" strokeWidth="1" fill="none" />
              </svg>
            ))}
          </div>

          <div className="grid grid-cols-4 lg:grid-cols-8 gap-4 lg:gap-2">
            {AGENTS.map((a, i) => {
              const AgentIcon = a.icon;
              const isActive = i === active;
              const isHero = a.hero && !isActive;
              return (
                <button
                  key={a.id}
                  onClick={() => setActive(i)}
                  className={`relative flex flex-col items-center text-center group transition-all duration-300 ${
                    visible ? "animate-fade-in" : "opacity-0"
                  }`}
                  style={{ animationDelay: `${i * 80}ms` }}
                >
                  <div className="relative">
                    {/* D2 pulse ring when not active */}
                    {isHero && (
                      <div className="absolute inset-0 rounded-xl animate-pulseRing" />
                    )}
                    <div
                      className={`w-[74px] h-[74px] rounded-xl flex items-center justify-center transition-all duration-300 relative ${
                        isActive
                          ? "bg-flame shadow-flame"
                          : "bg-ink-850 border border-white/[0.06] hover:border-white/10"
                      }`}
                    >
                      <AgentIcon className={`w-6 h-6 transition-colors ${isActive ? "text-white" : "text-ink-400 group-hover:text-ink-200"}`} />
                      {/* ID in corner */}
                      <span className={`absolute top-1.5 right-2 text-[9px] font-mono ${isActive ? "text-white/70" : "text-ink-600"}`}>
                        {a.id}
                      </span>
                    </div>
                  </div>
                  <span className={`mt-2 text-xs font-medium ${isActive ? "text-white" : "text-ink-400"}`}>{a.name}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Detail card */}
        <div className="mt-10 max-w-2xl mx-auto">
          <div className="bg-ink-900 border border-white/[0.06] rounded-xl p-6 shadow-card-glow transition-all duration-300 border-l-4 border-l-flame">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-lg bg-flame/10 border border-flame/30 flex items-center justify-center">
                <Icon className="w-5 h-5 text-flame" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-flame">{agent.id}</span>
                  <span className="text-[10px] font-mono text-ink-500 px-1.5 py-0.5 bg-ink-800 rounded">{agent.tag}</span>
                </div>
                <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
              </div>
            </div>
            <p className="text-sm text-ink-300 leading-relaxed mb-3">{agent.detail}</p>
            <div className="flex flex-wrap gap-1.5">
              {agent.tags.map((t) => (
                <span key={t} className="text-[10px] font-mono px-2 py-0.5 bg-ink-800 border border-white/[0.04] rounded text-ink-300">{t}</span>
              ))}
            </div>
          </div>

          {/* Approval gate explainer */}
          <div className="mt-4 flex items-center gap-3 px-4 py-3 bg-ink-900/50 border border-white/[0.04] rounded-lg">
            <div className="w-2 h-2 rounded-full bg-moss animate-blink" />
            <p className="text-xs text-ink-400">
              <span className="text-ink-200 font-medium">Approval gate</span> — After every agent, a human reviews and approves before the next stage begins.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   ConflictDemo — Interactive conflict viewer
   ─────────────────────────────────────────────── */

function ConflictDemo() {
  const { ref, visible } = useOnScreen();
  const [activeConflict, setActiveConflict] = useState(0);
  const conflict = CONFLICTS[activeConflict];

  const severityDot: Record<string, string> = {
    critical: "bg-flame",
    high: "bg-flame",
    medium: "bg-ink-500",
  };

  const severityLabel: Record<string, string> = {
    critical: "text-flame",
    high: "text-flame",
    medium: "text-ink-400",
  };

  return (
    <section id="conflict-demo" className="py-28 bg-ink-900/50 relative" ref={ref}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-14">
          <p className="text-xs font-mono uppercase tracking-widest text-flame mb-3">Live preview</p>
          <h2 className="display text-3xl md:text-5xl font-bold tracking-tight text-white">
            The wow moment, in one screen
          </h2>
          <p className="mt-4 text-ink-300 max-w-2xl mx-auto">
            D8X reads your docs and surfaces the contradictions hiding between them. Click through real examples below.
          </p>
        </div>

        <div className={`bg-ink-900 border border-white/[0.06] rounded-xl overflow-hidden shadow-card-glow ${visible ? "animate-fade-in" : "opacity-0"}`}>
          {/* Mock browser chrome */}
          <div className="flex items-center gap-3 px-4 py-3 bg-ink-850 border-b border-white/[0.04]">
            <div className="flex gap-1.5">
              <div className="w-2.5 h-2.5 rounded-full bg-ink-600" />
              <div className="w-2.5 h-2.5 rounded-full bg-ink-600" />
              <div className="w-2.5 h-2.5 rounded-full bg-ink-600" />
            </div>
            <div className="flex-1 flex items-center justify-center">
              <span className="text-[10px] font-mono text-ink-500">D2 Discover &middot; Run #47 &middot; 3 conflicts found</span>
            </div>
          </div>

          {/* Split layout */}
          <div className="grid lg:grid-cols-[280px_1fr]">
            {/* Sidebar — conflict list */}
            <div className="border-r border-white/[0.04] p-3 space-y-1">
              {CONFLICTS.map((c, i) => (
                <button
                  key={c.id}
                  onClick={() => setActiveConflict(i)}
                  className={`w-full text-left p-3 rounded-lg transition-all duration-200 ${
                    i === activeConflict
                      ? "bg-ink-800 border-l-2 border-l-flame"
                      : "hover:bg-ink-850"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <div className={`w-2 h-2 rounded-full flex-shrink-0 ${severityDot[c.severity]}`} />
                    <span className="text-[10px] font-mono text-ink-500">{c.id}</span>
                  </div>
                  <span className={`text-xs font-medium ${i === activeConflict ? "text-white" : "text-ink-300"}`}>
                    {c.title}
                  </span>
                </button>
              ))}
            </div>

            {/* Main panel — detail */}
            <div className="p-6">
              {/* Header */}
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-2.5 h-2.5 rounded-full ${severityDot[conflict.severity]}`} />
                <span className="text-xs font-mono text-ink-500">{conflict.id}</span>
                <span className={`text-xs font-medium uppercase ${severityLabel[conflict.severity]}`}>{conflict.severity}</span>
              </div>

              <h3 className="text-xl font-semibold text-white mb-2">{conflict.title}</h3>
              <p className="text-sm text-ink-300 mb-6">{conflict.summary}</p>

              {/* Confidence score */}
              <div className="flex items-center gap-4 mb-6">
                <span className="num text-4xl font-bold text-white">{conflict.confidence}<span className="text-xl text-ink-400">%</span></span>
                <span className="text-xs text-ink-400">confidence score</span>
              </div>

              {/* Source rows grid */}
              <div className="space-y-3 mb-6">
                {conflict.sources.map((src, i) => (
                  <div key={i} className="p-4 bg-ink-850 border border-white/[0.04] rounded-lg">
                    <div className="flex items-center gap-3 mb-2">
                      <span className={`text-[10px] font-mono font-medium px-2 py-0.5 rounded ${
                        src.conflict ? "bg-flame/10 text-flame border border-flame/20" : "bg-ink-700 text-ink-300 border border-white/[0.04]"
                      }`}>
                        {src.kind}
                      </span>
                      <span className="text-[11px] text-ink-400">{src.loc}</span>
                    </div>
                    <p className="text-xs text-ink-200 font-mono leading-relaxed mb-2">{src.quote}</p>
                    <span className={`inline-block text-[10px] font-mono font-medium px-2 py-0.5 rounded ${
                      src.conflict ? "bg-flame/10 text-flame" : "bg-ink-700 text-ink-300"
                    }`}>
                      {src.value}
                    </span>
                  </div>
                ))}
              </div>

              {/* Resolution */}
              <div className="p-4 bg-ink-850 border border-white/[0.04] rounded-lg">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs font-medium text-ink-200">Recommended resolution</span>
                </div>
                <p className="text-sm text-ink-300 mb-3">{conflict.rec}</p>
                <button className="inline-flex items-center gap-2 px-4 py-2 text-xs font-medium bg-flame text-white rounded-lg hover:bg-flame-deep transition-colors">
                  Resolve
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   HowItWorks — 3 step cards
   ─────────────────────────────────────────────── */

function HowItWorks() {
  const { ref, visible } = useOnScreen();

  return (
    <section id="how" className="py-28 bg-ink-950 relative" ref={ref}>
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-xs font-mono uppercase tracking-widest text-flame mb-3">How it works</p>
          <h2 className="display text-3xl md:text-5xl font-bold tracking-tight text-white">
            Three steps. Full pipeline.
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {STEPS.map((s, i) => {
            const StepIcon = s.icon;
            return (
              <div
                key={s.step}
                className={`relative bg-ink-900 border border-white/[0.06] rounded-xl p-6 shadow-card-glow ${
                  visible ? "animate-slide-up" : "opacity-0"
                }`}
                style={{ animationDelay: `${i * 150}ms` }}
              >
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 rounded-lg bg-ink-800 border border-white/[0.06] flex items-center justify-center">
                    <StepIcon className="w-5 h-5 text-flame" />
                  </div>
                  <span className="num text-3xl font-bold text-ink-700">{s.step}</span>
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{s.title}</h3>
                <p className="text-sm text-ink-300 leading-relaxed">{s.desc}</p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   BuiltWith — Tech stack grid
   ─────────────────────────────────────────────── */

function BuiltWith() {
  const { ref, visible } = useOnScreen();

  return (
    <section id="tech" className="py-28 bg-ink-900/30 relative" ref={ref}>
      <div className="max-w-5xl mx-auto px-6">
        <div className="text-center mb-16">
          <p className="text-xs font-mono uppercase tracking-widest text-flame mb-3">Stack</p>
          <h2 className="display text-3xl md:text-5xl font-bold tracking-tight text-white">
            Built with
          </h2>
          <p className="mt-4 text-ink-300 max-w-2xl mx-auto">
            Modern foundations. Production-grade architecture.
          </p>
        </div>

        <div className={`grid sm:grid-cols-2 lg:grid-cols-3 gap-4 ${visible ? "animate-fade-in" : "opacity-0"}`}>
          {TECH_STACK.map((t) => (
            <div key={t.name} className="bg-ink-900 border border-white/[0.06] rounded-xl p-5 shadow-card-glow">
              <h3 className="text-sm font-semibold text-white mb-1">{t.name}</h3>
              <p className="text-xs text-ink-400">{t.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   FAQ — Accordion with smooth transition
   ─────────────────────────────────────────────── */

function FAQ() {
  const { ref, visible } = useOnScreen();
  const [openIndex, setOpenIndex] = useState<number | null>(null);

  return (
    <section id="faq" className="py-28 bg-ink-950 relative" ref={ref}>
      <div className="max-w-3xl mx-auto px-6">
        <div className="text-center mb-14">
          <p className="text-xs font-mono uppercase tracking-widest text-flame mb-3">FAQ</p>
          <h2 className="display text-3xl md:text-4xl font-bold tracking-tight text-white">
            Common questions
          </h2>
        </div>

        <div className={`space-y-2 ${visible ? "animate-fade-in" : "opacity-0"}`}>
          {FAQS.map((faq, i) => {
            const isOpen = openIndex === i;
            return (
              <div key={i} className="border border-white/[0.06] rounded-lg overflow-hidden">
                <button
                  onClick={() => setOpenIndex(isOpen ? null : i)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-white/[0.02] transition-colors"
                >
                  <span className="text-sm font-medium text-ink-100 pr-4">{faq.q}</span>
                  {isOpen ? (
                    <Minus className="w-4 h-4 text-ink-400 flex-shrink-0" />
                  ) : (
                    <Plus className="w-4 h-4 text-ink-400 flex-shrink-0" />
                  )}
                </button>
                <div
                  className="transition-all duration-300 overflow-hidden"
                  style={{ maxHeight: isOpen ? "300px" : "0px", opacity: isOpen ? 1 : 0 }}
                >
                  <div className="px-4 pb-4">
                    <p className="text-sm text-ink-300 leading-relaxed">{faq.a}</p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Footer
   ─────────────────────────────────────────────── */

function Footer() {
  return (
    <footer className="bg-ink-950 border-t hairline">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="flex flex-col md:flex-row items-start justify-between gap-8">
          {/* Logo column */}
          <div>
            <div className="flex items-center gap-2.5">
              <D8XLogo />
              <span className="display text-[19px] font-semibold text-white">D8X</span>
            </div>
            <p className="mt-3 text-xs text-ink-400 leading-relaxed max-w-[240px]">
              Eight AI agents. One pipeline. Zero blind spots.
            </p>
          </div>

          {/* Links */}
          <div className="flex gap-8">
            {[
              { label: "Try Demo", href: "/projects/new" },
              { label: "Book a Demo", href: "/book-demo" },
              { label: "Contact", href: "mailto:hello@d8x.com" },
            ].map((link) => (
              <a
                key={link.label}
                href={link.href}
                className="text-xs text-ink-400 hover:text-white transition-colors"
              >
                {link.label}
              </a>
            ))}
          </div>
        </div>

        <div className="mt-12 pt-6 border-t hairline flex items-center justify-between text-xs text-ink-500">
          <span>&copy; 2026 D8X, Inc. All rights reserved.</span>
          <span className="inline-flex items-center gap-1.5 num uppercase tracking-wider text-[10px]">
            <span className="w-1 h-1 rounded-full bg-flame" />
            Patent pending &mdash; Cross-source conflict detection
          </span>
        </div>
      </div>
    </footer>
  );
}

/* ───────────────────────────────────────────────
   Page Assembly
   ─────────────────────────────────────────────── */

export default function LandingPage() {
  return (
    <div className="bg-ink-950 text-white antialiased">
      <Nav />
      <Hero />
      <Pipeline />
      <ConflictDemo />
      <HowItWorks />
      <BuiltWith />
      <FAQ />
      <Footer />
    </div>
  );
}
