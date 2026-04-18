"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";

/* ───────────────────────────────────────────────
   D8X Brand Constants
   ─────────────────────────────────────────────── */

const AGENTS = [
  { id: "D1", name: "Ingest", icon: "📥", color: "#2E86C1", desc: "Parse any input — PDFs, code, audio, video, images" },
  { id: "D2", name: "Discover", icon: "🔍", color: "#2E86C1", desc: "Extract rules, entities, conflicts, system understanding" },
  { id: "D3", name: "Design", icon: "📐", color: "#2E86C1", desc: "Architecture, DB schema, API contracts, auth model" },
  { id: "D4", name: "Prototype", icon: "🖥️", color: "#F5C518", desc: "Live interactive demo at a real URL for stakeholders" },
  { id: "D5", name: "Plan", icon: "📋", color: "#F5C518", desc: "Epics, sequenced stories, detailed acceptance criteria" },
  { id: "D6", name: "Build", icon: "🔨", color: "#F5C518", desc: "Story-by-story code generation with GitHub PRs" },
  { id: "D7", name: "Test", icon: "🛡️", color: "#2E86C1", desc: "QA, security scans, accessibility, API validation" },
  { id: "D8", name: "Ship", icon: "🚀", color: "#2E86C1", desc: "Deploy, monitor, error feedback loop to Build" },
] as const;

const BOOK_DEMO_URL = "/book-demo";

/* ───────────────────────────────────────────────
   Intersection Observer hook
   ─────────────────────────────────────────────── */

function useOnScreen(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setVisible(true); }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold]);
  return { ref, visible };
}

/* ───────────────────────────────────────────────
   Nav
   ─────────────────────────────────────────────── */

function Nav() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const h = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", h, { passive: true });
    return () => window.removeEventListener("scroll", h);
  }, []);

  return (
    <nav className={`fixed top-0 w-full z-50 transition-all duration-300 ${scrolled ? "bg-d8x-slate/95 backdrop-blur-md border-b border-white/5 shadow-lg" : ""}`}>
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="#" className="flex items-center gap-2">
          <span className="text-2xl font-black tracking-tighter">
            D8<span className="text-d8x-gold">X</span>
          </span>
        </a>
        <div className="hidden md:flex items-center gap-8 text-sm text-gray-400">
          <a href="#pipeline" className="hover:text-white transition-colors">Pipeline</a>
          <a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a>
          <a href="#comparison" className="hover:text-white transition-colors">Compare</a>
          <a href="#use-cases" className="hover:text-white transition-colors">Use Cases</a>
          <Link href="/demo" className="hover:text-white transition-colors">Live Demo</Link>
        </div>
        <Link href={BOOK_DEMO_URL} className="btn-primary !py-2 !px-5 text-sm">
          Book a Demo
        </Link>
      </div>
    </nav>
  );
}

/* ───────────────────────────────────────────────
   Section 1: Hero
   ─────────────────────────────────────────────── */

function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-b from-d8x-navy-deep/50 via-d8x-slate to-d8x-slate" />
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-d8x-blue/10 rounded-full blur-[120px]" />
      <div className="absolute top-1/3 right-1/4 w-[300px] h-[300px] bg-d8x-gold/5 rounded-full blur-[100px]" />

      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-d8x-gold/30 bg-d8x-gold/5 text-d8x-gold text-sm font-medium mb-8">
          <span className="w-2 h-2 rounded-full bg-d8x-gold animate-pulse" />
          Patent Pending
        </div>

        <h1 className="text-5xl md:text-7xl lg:text-8xl font-black tracking-tight leading-[0.95]">
          Eight AI agents.
          <br />
          <span className="bg-gradient-to-r from-d8x-gold via-d8x-gold-light to-d8x-gold bg-clip-text text-transparent">
            One complete SDLC.
          </span>
        </h1>

        <p className="mt-6 text-xl md:text-2xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
          D8X takes your project from requirements to production with 8 specialized AI agents — each one an expert at its stage, all connected by a shared knowledge graph.
        </p>

        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href={BOOK_DEMO_URL} className="btn-primary text-lg">
            Book a Demo
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
          </Link>
          <Link href="/demo" className="btn-secondary text-lg">
            See It In Action
          </Link>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-10 left-1/2 -translate-x-1/2">
          <div className="w-6 h-10 border-2 border-white/20 rounded-full flex items-start justify-center pt-2">
            <div className="w-1.5 h-3 bg-white/40 rounded-full animate-bounce" />
          </div>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Section 2: Pipeline Visualization
   ─────────────────────────────────────────────── */

function Pipeline() {
  const { ref, visible } = useOnScreen();
  const [activeAgent, setActiveAgent] = useState(0);

  useEffect(() => {
    if (!visible) return;
    const t = setInterval(() => setActiveAgent((p) => (p + 1) % 8), 2000);
    return () => clearInterval(t);
  }, [visible]);

  return (
    <section id="pipeline" className="py-32 relative" ref={ref}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="section-heading">The D8X Pipeline</h2>
          <p className="section-subheading">
            Eight agents, each a specialist. Connected by a shared Business Context Store so every decision builds on the last.
          </p>
        </div>

        {/* Pipeline flow */}
        <div className="relative">
          {/* Connection line */}
          <div className="hidden lg:block absolute top-1/2 left-[6%] right-[6%] h-0.5 bg-white/10 -translate-y-1/2" />
          <div className="hidden lg:block absolute top-1/2 left-[6%] h-0.5 bg-gradient-to-r from-d8x-gold to-d8x-blue -translate-y-1/2 transition-all duration-1000"
               style={{ width: `${(activeAgent / 7) * 88}%` }} />

          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-4">
            {AGENTS.map((agent, i) => (
              <div
                key={agent.id}
                className={`relative flex flex-col items-center text-center transition-all duration-500 ${
                  visible ? "animate-fade-in" : "opacity-0"
                } stagger-${i + 1}`}
              >
                {/* Node */}
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center text-2xl transition-all duration-500 ${
                  i <= activeAgent
                    ? "bg-gradient-to-br from-d8x-navy to-d8x-blue shadow-lg shadow-d8x-blue/30 scale-110"
                    : "bg-d8x-slate-light border border-white/10"
                }`}>
                  {agent.icon}
                </div>

                {/* Label */}
                <div className="mt-3">
                  <span className="text-[10px] font-mono text-d8x-gold">{agent.id}</span>
                  <p className={`text-sm font-semibold mt-0.5 transition-colors ${i <= activeAgent ? "text-white" : "text-gray-500"}`}>
                    {agent.name}
                  </p>
                </div>

                {/* Description tooltip */}
                <p className="text-[11px] text-gray-500 mt-2 leading-tight max-w-[120px]">
                  {agent.desc}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Data flow particles */}
        <div className="mt-12 h-12 relative overflow-hidden rounded-lg bg-d8x-slate-light/50 border border-white/5">
          <div className="absolute inset-y-0 left-0 w-full flex items-center">
            {[0, 1, 2].map((i) => (
              <div key={i} className="absolute h-1 w-20 rounded-full bg-gradient-to-r from-transparent via-d8x-gold to-transparent animate-data-flow"
                   style={{ animationDelay: `${i * 1.3}s` }} />
            ))}
          </div>
          <div className="absolute inset-0 flex items-center justify-center text-xs font-mono text-gray-500">
            Business Context Store — shared knowledge graph across all 8 agents
          </div>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Section 3: How It Works
   ─────────────────────────────────────────────── */

function HowItWorks() {
  const { ref, visible } = useOnScreen();
  const steps = [
    {
      step: "01",
      title: "Upload your inputs",
      desc: "Drop in BRDs, source code, meeting recordings, wireframes, database schemas — any format. The Ingest agent parses everything into structured text.",
      icon: "📁",
      formats: ["PDF", "DOCX", "MP4", "Python", "SQL", "PNG"],
    },
    {
      step: "02",
      title: "AI agents analyze, design, build",
      desc: "Eight specialized agents work in sequence. Each one reads everything the previous agents produced. Discover extracts rules. Design creates architecture. Build writes code.",
      icon: "🤖",
      formats: ["Rules", "Entities", "Schema", "APIs", "Code", "Tests"],
    },
    {
      step: "03",
      title: "Review and approve at every stage",
      desc: "Human-in-the-loop gates between every phase. Approve to proceed, reject to stop, or request revisions with feedback. You stay in control.",
      icon: "✅",
      formats: ["Approve", "Reject", "Revise", "Feedback", "Preview", "Deploy"],
    },
  ];

  return (
    <section id="how-it-works" className="py-32 bg-gradient-to-b from-d8x-slate to-d8x-navy-deep/30" ref={ref}>
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-20">
          <h2 className="section-heading">How D8X Works</h2>
          <p className="section-subheading">Three steps from requirements to production.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-8">
          {steps.map((s, i) => (
            <div key={s.step} className={`card relative group ${visible ? "animate-slide-up" : "opacity-0"} stagger-${i + 1}`}>
              <div className="absolute -top-4 -left-2 text-6xl font-black text-d8x-navy-light/50 select-none">
                {s.step}
              </div>
              <div className="relative pt-8">
                <div className="text-4xl mb-4">{s.icon}</div>
                <h3 className="text-xl font-bold mb-3">{s.title}</h3>
                <p className="text-gray-400 text-sm leading-relaxed">{s.desc}</p>
                <div className="flex flex-wrap gap-2 mt-4">
                  {s.formats.map((f) => (
                    <span key={f} className="px-2 py-0.5 text-xs font-mono bg-d8x-navy/50 text-d8x-blue-light rounded border border-d8x-blue/20">
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Section 4: Comparison Table
   ─────────────────────────────────────────────── */

function Comparison() {
  const { ref, visible } = useOnScreen();
  const rows = [
    { feature: "Requirements analysis", d8x: "Automated", manual: "Weeks of BA work", competitor: "Partial" },
    { feature: "System design", d8x: "Generated + reviewed", manual: "Architect + weeks", competitor: "Not included" },
    { feature: "Interactive prototype", d8x: "Live URL in minutes", manual: "Figma + dev time", competitor: "Not included" },
    { feature: "Story generation", d8x: "AI + human approval", manual: "PM writes manually", competitor: "Basic backlog" },
    { feature: "Code generation", d8x: "Full-stack from stories", manual: "Developer team", competitor: "Single files" },
    { feature: "QA & security", d8x: "Automated pipeline", manual: "Separate QA team", competitor: "Not included" },
    { feature: "Deployment", d8x: "CI/CD + monitoring", manual: "DevOps team", competitor: "Not included" },
    { feature: "Human oversight", d8x: "Approval gates", manual: "Built-in", competitor: "None" },
    { feature: "Cross-phase context", d8x: "Shared knowledge graph", manual: "Tribal knowledge", competitor: "None" },
  ];

  return (
    <section id="comparison" className="py-32" ref={ref}>
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="section-heading">Legacy tools do one thing.<br /><span className="text-d8x-gold">D8X does everything.</span></h2>
          <p className="section-subheading">End-to-end coverage. No handoff gaps.</p>
        </div>

        <div className={`overflow-x-auto ${visible ? "animate-fade-in" : "opacity-0"}`}>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10">
                <th className="text-left py-4 px-4 text-gray-400 font-medium w-1/4" />
                <th className="py-4 px-4 text-center">
                  <span className="text-lg font-bold">D8<span className="text-d8x-gold">X</span></span>
                </th>
                <th className="py-4 px-4 text-center text-gray-400">Manual SDLC</th>
                <th className="py-4 px-4 text-center text-gray-400">AI Copilots</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={row.feature} className="border-b border-white/5 hover:bg-white/[0.02] transition-colors">
                  <td className="py-3 px-4 text-gray-300">{row.feature}</td>
                  <td className="py-3 px-4 text-center">
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-d8x-gold/10 text-d8x-gold text-xs font-medium rounded-full">
                      <span className="w-1.5 h-1.5 rounded-full bg-d8x-gold" />
                      {row.d8x}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-center text-gray-500">{row.manual}</td>
                  <td className="py-3 px-4 text-center text-gray-500">{row.competitor}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Section 5: Use Cases
   ─────────────────────────────────────────────── */

function UseCases() {
  const { ref, visible } = useOnScreen();
  const cases = [
    {
      title: "Legacy Modernization",
      desc: "Upload your legacy code + documentation. D8X reverse-engineers the system, designs a modern replacement, generates a prototype for stakeholder approval, then builds it — story by story.",
      tags: ["COBOL", "VB6", "Java EE", "Oracle Forms"],
      icon: "🏗️",
    },
    {
      title: "Greenfield Development",
      desc: "Start from a BRD or even a meeting recording. D8X discovers requirements, designs the architecture, and builds a production-ready application with tests and deployment pipeline.",
      tags: ["Startup MVP", "Internal Tools", "SaaS"],
      icon: "🌱",
    },
    {
      title: "Enterprise Compliance",
      desc: "Every decision is traceable to a requirement. Every approval is recorded. Every security scan is documented. Built for SOC2, HIPAA, and FedRAMP audit trails.",
      tags: ["SOC2", "HIPAA", "FedRAMP", "Audit Trail"],
      icon: "🔒",
    },
  ];

  return (
    <section id="use-cases" className="py-32 bg-gradient-to-b from-d8x-slate to-d8x-navy-deep/30" ref={ref}>
      <div className="max-w-6xl mx-auto px-6">
        <div className="text-center mb-16">
          <h2 className="section-heading">Built for real projects</h2>
          <p className="section-subheading">Not a toy. Not a demo. Production-grade output from day one.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {cases.map((c, i) => (
            <div key={c.title} className={`card group ${visible ? "animate-slide-up" : "opacity-0"} stagger-${i + 1}`}>
              <div className="text-4xl mb-4">{c.icon}</div>
              <h3 className="text-xl font-bold mb-3">{c.title}</h3>
              <p className="text-gray-400 text-sm leading-relaxed mb-4">{c.desc}</p>
              <div className="flex flex-wrap gap-2">
                {c.tags.map((t) => (
                  <span key={t} className="px-2 py-0.5 text-xs bg-white/5 text-gray-400 rounded border border-white/10">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Section 6: Patent Badge
   ─────────────────────────────────────────────── */

function PatentBadge() {
  return (
    <section className="py-20">
      <div className="max-w-4xl mx-auto px-6 text-center">
        <div className="inline-flex flex-col items-center gap-4 p-8 rounded-2xl border border-d8x-gold/20 bg-gradient-to-b from-d8x-gold/5 to-transparent">
          <div className="flex items-center gap-3">
            <svg className="w-8 h-8 text-d8x-gold" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
            <span className="text-2xl font-bold text-d8x-gold">Patent Pending</span>
          </div>
          <p className="text-gray-400 text-sm max-w-lg">
            The D8X multi-agent pipeline architecture — 8 specialized AI agents connected by a shared Business Context Store with human-in-the-loop approval gates — is patent pending.
          </p>
        </div>
      </div>
    </section>
  );
}

/* ───────────────────────────────────────────────
   Section 7: Footer CTA
   ─────────────────────────────────────────────── */

function Footer() {
  return (
    <footer className="py-32 relative overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-t from-d8x-navy-deep to-d8x-slate" />
      <div className="absolute bottom-0 left-1/2 -translate-x-1/2 w-[800px] h-[400px] bg-d8x-blue/5 rounded-full blur-[120px]" />

      <div className="relative z-10 max-w-4xl mx-auto px-6 text-center">
        <h2 className="text-4xl md:text-6xl font-black tracking-tight">
          Ready to ship<br />
          <span className="text-d8x-gold">10x faster?</span>
        </h2>
        <p className="mt-6 text-xl text-gray-400 max-w-xl mx-auto">
          See D8X process a real legacy application in under 30 minutes. No slides, no scripted demo — live agents, real output.
        </p>
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href={BOOK_DEMO_URL} className="btn-primary text-lg">
            Book a Demo
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
          </Link>
          <Link href="/demo" className="btn-secondary text-lg">
            Watch the Walkthrough
          </Link>
        </div>

        <div className="mt-20 pt-8 border-t border-white/10 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-gray-500">
          <span className="font-bold text-white">D8<span className="text-d8x-gold">X</span></span>
          <span>&copy; {new Date().getFullYear()} D8X Inc. All rights reserved. Patent pending.</span>
          <div className="flex gap-6">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">Terms</a>
            <a href="mailto:hello@d8x.ai" className="hover:text-white transition-colors">Contact</a>
          </div>
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
    <>
      <Nav />
      <Hero />
      <Pipeline />
      <HowItWorks />
      <Comparison />
      <UseCases />
      <PatentBadge />
      <Footer />
    </>
  );
}
