"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";

/* ───────────────────────────────────────────────
   Terminal simulation data — real D8X agent output
   ─────────────────────────────────────────────── */

interface TerminalLine {
  text: string;
  type: "command" | "output" | "success" | "info" | "header" | "blank";
  delay?: number; // ms to wait before showing next line
}

const AGENT_SEQUENCES: { agent: string; id: string; color: string; lines: TerminalLine[] }[] = [
  {
    agent: "D1: Ingest",
    id: "ingest",
    color: "#38bdf8",
    lines: [
      { text: "$ d8x ingest --project inventorypro --files ./legacy/", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Ingesting 4 files...", type: "info", delay: 400 },
      { text: "  [PDF]   brd.md ············· 3,200 words  BRD detected", type: "output", delay: 300 },
      { text: "  [Code]  source_code.py ····· 250 lines   Flask + SQLAlchemy", type: "output", delay: 300 },
      { text: "  [Notes] meeting_notes.md ··· 1,800 words  Meeting notes", type: "output", delay: 300 },
      { text: "  [SQL]   schema.sql ········· 8 tables     PostgreSQL DDL", type: "output", delay: 300 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Content classified: 1 BRD, 1 codebase, 1 meeting notes, 1 schema", type: "info", delay: 400 },
      { text: "  Quality score: 87/100  PASS", type: "success", delay: 400 },
      { text: "  Stored 4 sources to Business Context Store", type: "success", delay: 500 },
    ],
  },
  {
    agent: "D2: Discover",
    id: "discover",
    color: "#38bdf8",
    lines: [
      { text: "$ d8x discover --project inventorypro", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Loading 4 ingested sources from context store...", type: "info", delay: 600 },
      { text: "  Running business rule extraction...", type: "info", delay: 800 },
      { text: "    Found 15 business rules (12 high-confidence, 3 inferred)", type: "output", delay: 400 },
      { text: "  Running entity extraction...", type: "info", delay: 600 },
      { text: "    Found 15 domain entities (User, Order, Product, Supplier...)", type: "output", delay: 400 },
      { text: "  Running conflict detection across all sources...", type: "info", delay: 800 },
      { text: "    5 contradictions  8 gaps  4 ambiguities  3 redundancies", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  CONFLICT: BRD says $5K approval threshold, code says $10K", type: "output", delay: 500 },
      { text: "  CONFLICT: BRD says 3 login attempts, code allows 5", type: "output", delay: 400 },
      { text: "  GAP: Warehouse Staff role in BRD but missing from code", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Quality: 81.1/100  PASS", type: "success", delay: 400 },
      { text: "  Generated 8 clarification questions for product owner", type: "success", delay: 500 },
    ],
  },
  {
    agent: "D3: Design",
    id: "design",
    color: "#38bdf8",
    lines: [
      { text: "$ d8x design --project inventorypro", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Loading discovery context (15 rules, 15 entities)...", type: "info", delay: 600 },
      { text: "  Generating architecture decision...", type: "info", delay: 1000 },
      { text: "    Pattern: modular_monolith (FastAPI + Next.js + PostgreSQL)", type: "output", delay: 400 },
      { text: "  Generating database schema...", type: "info", delay: 800 },
      { text: "    12 tables, 18 indexes, 15 FK relationships, soft delete", type: "output", delay: 400 },
      { text: "  Generating API contracts...", type: "info", delay: 800 },
      { text: "    42 endpoints across 8 resources, OpenAPI 3.1 spec", type: "output", delay: 400 },
      { text: "  Generating auth design...", type: "info", delay: 600 },
      { text: "    JWT + RBAC, 4 roles, 24 permissions, bcrypt + rate limiting", type: "output", delay: 400 },
      { text: "  Generating frontend architecture...", type: "info", delay: 600 },
      { text: "    14 pages, 32 components, React Query + Zustand", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Quality: 82.8/100  PASS", type: "success", delay: 400 },
      { text: "  Stored 5 design artifacts", type: "success", delay: 500 },
    ],
  },
  {
    agent: "D4: Prototype",
    id: "prototype",
    color: "#ff7a3a",
    lines: [
      { text: "$ d8x prototype --project inventorypro --provider s3_static", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Interpreting design artifacts into prototype spec...", type: "info", delay: 800 },
      { text: "    14 pages, 32 components, 5 mock data models, 8 API mocks", type: "output", delay: 400 },
      { text: "  Generating Next.js 14 application...", type: "info", delay: 1200 },
      { text: "    Generated 47 files (pages, components, layouts, API mocks)", type: "output", delay: 400 },
      { text: "    shadcn/ui + Tailwind CSS, responsive design, role-based views", type: "output", delay: 400 },
      { text: "  Validating prototype...", type: "info", delay: 600 },
      { text: "    14/14 routes present, package.json valid, 0 errors, 2 warnings", type: "output", delay: 400 },
      { text: "  Deploying to S3 preview...", type: "info", delay: 1000 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Preview URL: https://preview.d8x.ai/inventorypro-v1", type: "success", delay: 400 },
      { text: "  Quality: 78.3/100  PASS", type: "success", delay: 500 },
    ],
  },
  {
    agent: "D5: Plan",
    id: "plan",
    color: "#ff7a3a",
    lines: [
      { text: "$ d8x plan --project inventorypro", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Loading design + prototype + business context...", type: "info", delay: 600 },
      { text: "  Generating implementation plan...", type: "info", delay: 1000 },
      { text: "    6 epics, 34 user stories, topologically sorted", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Epic 1: Authentication & Authorization (8 stories, 21 pts)", type: "output", delay: 300 },
      { text: "  Epic 2: Product & Inventory Management (7 stories, 18 pts)", type: "output", delay: 300 },
      { text: "  Epic 3: Order Processing & Approval (6 stories, 16 pts)", type: "output", delay: 300 },
      { text: "  Epic 4: Reporting & Analytics (5 stories, 13 pts)", type: "output", delay: 300 },
      { text: "  Epic 5: Supplier Integration (4 stories, 11 pts)", type: "output", delay: 300 },
      { text: "  Epic 6: Mobile Warehouse Interface (4 stories, 10 pts)", type: "output", delay: 300 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Total: 89 story points, est. 4-6 sprints", type: "success", delay: 500 },
    ],
  },
  {
    agent: "D6: Build",
    id: "build",
    color: "#ff7a3a",
    lines: [
      { text: "$ d8x build --project inventorypro --epic 1", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Processing Story #1: \"User registration with email verification\"", type: "info", delay: 600 },
      { text: "    Generated: src/api/routes/auth.py (142 lines)", type: "output", delay: 400 },
      { text: "    Generated: src/services/auth_service.py (98 lines)", type: "output", delay: 400 },
      { text: "    Generated: tests/unit/test_auth.py (67 lines)", type: "output", delay: 400 },
      { text: "    Created PR #12: feat(auth): user registration with email verification", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Processing Story #2: \"JWT login with refresh token rotation\"", type: "info", delay: 600 },
      { text: "    Generated 3 files, 287 lines total", type: "output", delay: 400 },
      { text: "    Created PR #13: feat(auth): JWT login with refresh tokens", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Epic 1: 8/8 stories complete, 8 PRs created", type: "success", delay: 500 },
    ],
  },
  {
    agent: "D7: Test",
    id: "test",
    color: "#38bdf8",
    lines: [
      { text: "$ d8x test --project inventorypro", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Running E2E test suite (34 stories × 3 scenarios)...", type: "info", delay: 1000 },
      { text: "    98/102 test cases passed (96.1%)", type: "output", delay: 400 },
      { text: "  Running security scan...", type: "info", delay: 800 },
      { text: "    0 critical, 1 medium (missing rate limit on /api/export), 3 low", type: "output", delay: 400 },
      { text: "  Validating API contracts against OpenAPI spec...", type: "info", delay: 600 },
      { text: "    42/42 endpoints compliant", type: "output", delay: 400 },
      { text: "  Verifying acceptance criteria...", type: "info", delay: 600 },
      { text: "    32/34 stories verified, 2 need revision", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  QA Report: 91.2/100  PASS", type: "success", delay: 400 },
      { text: "  2 stories flagged for Build revision (feedback loop triggered)", type: "info", delay: 500 },
    ],
  },
  {
    agent: "D8: Ship",
    id: "ship",
    color: "#38bdf8",
    lines: [
      { text: "$ d8x ship --project inventorypro --target production", type: "command", delay: 800 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Building Docker images...", type: "info", delay: 800 },
      { text: "    d8x-inventorypro-api:1.0.0 (234MB)", type: "output", delay: 400 },
      { text: "    d8x-inventorypro-web:1.0.0 (187MB)", type: "output", delay: 400 },
      { text: "  Running database migrations...", type: "info", delay: 600 },
      { text: "    12 tables created, indexes built, seed data loaded", type: "output", delay: 400 },
      { text: "  Deploying to production...", type: "info", delay: 1000 },
      { text: "    API: https://api.inventorypro.example.com  HEALTHY", type: "output", delay: 400 },
      { text: "    Web: https://inventorypro.example.com  HEALTHY", type: "output", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  Monitoring dashboard: https://grafana.example.com/d/inventorypro", type: "info", delay: 400 },
      { text: "", type: "blank", delay: 200 },
      { text: "  SHIPPED. Project complete.", type: "success", delay: 800 },
    ],
  },
];

/* ───────────────────────────────────────────────
   Terminal Component
   ─────────────────────────────────────────────── */

function Terminal({ sequence, isActive, onComplete }: {
  sequence: typeof AGENT_SEQUENCES[0];
  isActive: boolean;
  onComplete: () => void;
}) {
  const [visibleLines, setVisibleLines] = useState<number>(0);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isActive) return;
    setVisibleLines(0);
    let i = 0;
    const showNext = () => {
      if (i >= sequence.lines.length) { onComplete(); return; }
      i++;
      setVisibleLines(i);
      const delay = sequence.lines[i - 1]?.delay ?? 300;
      setTimeout(showNext, delay);
    };
    const t = setTimeout(showNext, 500);
    return () => clearTimeout(t);
  }, [isActive, sequence, onComplete]);

  useEffect(() => {
    containerRef.current?.scrollTo({ top: containerRef.current.scrollHeight, behavior: "smooth" });
  }, [visibleLines]);

  return (
    <div className="rounded-xl border border-white/10 bg-ink-950 overflow-hidden shadow-2xl">
      {/* Title bar */}
      <div className="flex items-center gap-2 px-4 py-3 bg-ink-900 border-b border-white/5">
        <div className="flex gap-1.5">
          <span className="w-3 h-3 rounded-full bg-red-500/80" />
          <span className="w-3 h-3 rounded-full bg-flame" />
          <span className="w-3 h-3 rounded-full bg-green-500/80" />
        </div>
        <span className="ml-2 text-xs font-mono text-gray-500">{sequence.agent}</span>
        {isActive && visibleLines < sequence.lines.length && (
          <span className="ml-auto text-xs text-flame animate-pulse">processing...</span>
        )}
      </div>

      {/* Terminal body */}
      <div ref={containerRef} className="p-4 font-mono text-sm leading-relaxed h-[380px] overflow-y-auto">
        {sequence.lines.slice(0, visibleLines).map((line, i) => (
          <div key={i} className={`${
            line.type === "command" ? "text-flame font-bold" :
            line.type === "success" ? "text-green-400" :
            line.type === "info" ? "text-sky-400" :
            line.type === "blank" ? "h-3" :
            "text-gray-400"
          }`}>
            {line.text}
          </div>
        ))}
        {isActive && visibleLines < sequence.lines.length && (
          <span className="terminal-cursor text-gray-500" />
        )}
      </div>
    </div>
  );
}

/* ───────────────────────────────────────────────
   Agent Step Selector
   ─────────────────────────────────────────────── */

const BOOK_DEMO_URL = "/book-demo";

export default function DemoPage() {
  const [activeStep, setActiveStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [autoPlay, setAutoPlay] = useState(true);

  const handleComplete = useCallback(() => {
    setCompletedSteps((prev) => new Set(prev).add(activeStep));
    if (autoPlay && activeStep < AGENT_SEQUENCES.length - 1) {
      setTimeout(() => setActiveStep((p) => p + 1), 1000);
    }
  }, [activeStep, autoPlay]);

  return (
    <div className="min-h-screen bg-ink-900">
      {/* Nav */}
      <nav className="fixed top-0 w-full z-50 bg-ink-900/95 backdrop-blur-md border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <span className="text-2xl font-black tracking-tighter">
              D8<span className="text-flame">X</span>
            </span>
            <span className="text-sm text-gray-500 ml-2">/ Live Walkthrough</span>
          </Link>
          <Link href={BOOK_DEMO_URL} className="btn-primary !py-2 !px-5 text-sm">
            Book a Demo
          </Link>
        </div>
      </nav>

      <div className="pt-24 pb-16 max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl md:text-5xl font-black tracking-tight">
            Watch D8X process a <span className="text-flame">legacy inventory system</span>
          </h1>
          <p className="mt-4 text-lg text-gray-400 max-w-2xl mx-auto">
            4 source files in. Production-ready system out. Every agent shows its work.
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-center gap-4 mb-8">
          <button
            onClick={() => { setActiveStep(0); setCompletedSteps(new Set()); }}
            className="px-4 py-2 text-sm border border-white/10 rounded-lg hover:bg-white/5 transition-colors text-gray-400"
          >
            Restart
          </button>
          <button
            onClick={() => setAutoPlay(!autoPlay)}
            className={`px-4 py-2 text-sm rounded-lg transition-colors ${
              autoPlay ? "bg-flame/10 text-flame border border-flame/30" : "border border-white/10 text-gray-400 hover:bg-white/5"
            }`}
          >
            Auto-play: {autoPlay ? "ON" : "OFF"}
          </button>
        </div>

        <div className="grid lg:grid-cols-[280px_1fr] gap-8">
          {/* Step selector */}
          <div className="space-y-2">
            {AGENT_SEQUENCES.map((seq, i) => (
              <button
                key={seq.id}
                onClick={() => setActiveStep(i)}
                className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 flex items-center gap-3 ${
                  i === activeStep
                    ? "bg-ink-800 border border-sky-500/30 shadow-lg"
                    : completedSteps.has(i)
                    ? "bg-ink-800/50 border border-green-500/20"
                    : "border border-transparent hover:bg-white/[0.03]"
                }`}
              >
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                  completedSteps.has(i) ? "bg-green-500/20 text-green-400" :
                  i === activeStep ? "bg-sky-500/20 text-sky-400" :
                  "bg-white/5 text-gray-500"
                }`}>
                  {completedSteps.has(i) ? "✓" : `D${i + 1}`}
                </div>
                <div>
                  <div className={`text-sm font-medium ${i === activeStep ? "text-white" : "text-gray-400"}`}>
                    {seq.agent.split(": ")[1]}
                  </div>
                </div>
              </button>
            ))}

            {/* Summary when all complete */}
            {completedSteps.size === 8 && (
              <div className="mt-6 p-4 rounded-lg border border-flame/30 bg-flame/5">
                <div className="text-sm font-bold text-flame mb-1">Pipeline Complete</div>
                <div className="text-xs text-gray-400">
                  8 agents processed 27,534 characters of input into a production-ready system with 34 user stories, 42 API endpoints, and full test coverage.
                </div>
              </div>
            )}
          </div>

          {/* Terminal */}
          <Terminal
            key={activeStep}
            sequence={AGENT_SEQUENCES[activeStep]}
            isActive={true}
            onComplete={handleComplete}
          />
        </div>

        {/* Bottom CTA */}
        <div className="mt-16 text-center">
          <p className="text-gray-400 mb-6">Want to see this with your own codebase?</p>
          <Link href={BOOK_DEMO_URL} className="btn-primary">
            Book a Live Demo
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" /></svg>
          </Link>
        </div>
      </div>
    </div>
  );
}
