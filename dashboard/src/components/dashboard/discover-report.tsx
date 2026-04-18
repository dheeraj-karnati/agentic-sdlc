"use client";

import { AlertTriangle, ArrowRight, BookOpen, Bug, MessageCircleQuestion, Shield, MapPin } from "lucide-react";
import { QualityScore } from "./quality-score";

/* eslint-disable @typescript-eslint/no-explicit-any */

const CONF_BADGE: Record<string, string> = {
  high: "bg-green-500/15 text-green-400",
  medium: "bg-amber-500/15 text-amber-400",
  low: "bg-red-500/15 text-red-400",
};

const SEVERITY_BADGE: Record<string, string> = {
  critical: "bg-red-600/20 text-red-400 border border-red-500/30",
  blocking: "bg-red-600/20 text-red-400 border border-red-500/30",
  high: "bg-red-500/15 text-red-400",
  medium: "bg-amber-500/15 text-amber-400",
  low: "bg-blue-500/15 text-blue-400",
};

const TYPE_BADGE: Record<string, string> = {
  security_vulnerability: "bg-red-500/15 text-red-400",
  data_exposure: "bg-red-500/15 text-red-400",
  sql_injection: "bg-red-500/15 text-red-400",
  logic_bug: "bg-amber-500/15 text-amber-400",
  deprecated_code: "bg-amber-500/15 text-amber-400",
  data_conflict: "bg-blue-500/15 text-blue-400",
  implementation_gap: "bg-purple-500/15 text-purple-400",
  compliance_violation: "bg-orange-500/15 text-orange-400",
  ambiguity: "bg-gray-500/15 text-gray-400",
};

const ENTITY_TYPE_BADGE: Record<string, string> = {
  actor: "bg-purple-500/15 text-purple-400",
  core_entity: "bg-blue-500/15 text-blue-400",
  data_object: "bg-blue-500/15 text-blue-400",
  transaction: "bg-teal-500/15 text-teal-400",
  reference: "bg-gray-500/15 text-gray-400",
  junction: "bg-indigo-500/15 text-indigo-400",
  document: "bg-yellow-500/15 text-yellow-400",
  system: "bg-gray-500/15 text-gray-400",
  process: "bg-teal-500/15 text-teal-400",
};

export function DiscoverReport({ output }: { output: Record<string, any> }) {
  const metrics = output.metrics ?? {};
  const rules = (output.business_rules ?? []) as any[];
  const entities = (output.domain_entities ?? []) as any[];
  const conflicts = (output.conflicts ?? []) as any[];
  const defects = (output.defects ?? []) as any[];
  const questions = (output.clarification_questions ?? []) as any[];
  const understanding = output.system_understanding ?? {};
  const qa = output.quality_assessment ?? {};
  const score = metrics.quality_score ?? qa.score ?? 0;

  // Separate conflicts by category
  const securityIssues = conflicts.filter((c: any) =>
    ["security_vulnerability", "data_exposure", "compliance_violation"].includes(c.type)
  );
  const bugIssues = conflicts.filter((c: any) =>
    ["logic_bug", "deprecated_code"].includes(c.type)
  );
  const dataConflicts = conflicts.filter((c: any) =>
    !["security_vulnerability", "data_exposure", "compliance_violation", "logic_bug", "deprecated_code"].includes(c.type)
  );

  const criticalCount = conflicts.filter((c: any) => c.severity === "critical").length;
  const highCount = conflicts.filter((c: any) => c.severity === "high").length;

  return (
    <div className="space-y-5">
      {/* ── Section 1: Summary banner ── */}
      <div className="border-l-4 border-d8x-success bg-d8x-surface rounded-r-lg p-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">Discovery complete</h2>
          <p className="text-sm text-d8x-text-secondary mt-1">
            Analyzed all sources and extracted {rules.length} business rules, {entities.length} entities
            {conflicts.length > 0 ? `, and found ${conflicts.length} issue${conflicts.length > 1 ? "s" : ""}` : ""}.
          </p>
          {criticalCount > 0 && (
            <p className="text-xs text-red-400 mt-1 flex items-center gap-1">
              <AlertTriangle className="w-3.5 h-3.5" />
              {criticalCount} critical and {highCount} high severity issues require immediate attention
            </p>
          )}
        </div>
        {score > 0 && <QualityScore score={score} size={72} />}
      </div>

      {/* ── Section 2: Security & Vulnerabilities (shown first if critical) ── */}
      {securityIssues.length > 0 && (
        <div className="bg-d8x-surface border border-red-500/30 rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Shield className="w-4 h-4 text-red-400" />
            Security vulnerabilities ({securityIssues.length})
          </h3>
          <div className="space-y-2">
            {securityIssues.map((c: any, i: number) => (
              <div key={i} className="bg-red-500/5 border border-red-500/15 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium ${SEVERITY_BADGE[c.severity] ?? SEVERITY_BADGE.medium}`}>
                    {c.severity}
                  </span>
                  <p className="text-sm">{c.description}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${TYPE_BADGE[c.type] ?? TYPE_BADGE.ambiguity}`}>
                    {(c.type ?? "").replace(/_/g, " ")}
                  </span>
                  {c.location && (
                    <span className="text-[10px] text-d8x-text-tertiary flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> {c.location}
                    </span>
                  )}
                  {c.source_a && (
                    <span className="text-[10px] text-d8x-text-tertiary">
                      {c.source_a}{c.source_b && c.source_b !== c.source_a ? ` → ${c.source_b}` : ""}
                    </span>
                  )}
                </div>
                {c.resolution_options && c.resolution_options.length > 0 && (
                  <div className="mt-2 pl-2 border-l-2 border-d8x-border">
                    {(c.resolution_options as string[]).map((opt: string, j: number) => (
                      <p key={j} className="text-[11px] text-d8x-text-secondary">→ {opt}</p>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section 3: Bugs & Defects ── */}
      {bugIssues.length > 0 && (
        <div className="bg-d8x-surface border border-d8x-warning/30 rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <Bug className="w-4 h-4 text-d8x-warning" />
            Bugs & defects ({bugIssues.length})
          </h3>
          <div className="space-y-2">
            {bugIssues.map((c: any, i: number) => (
              <div key={i} className="bg-d8x-warning/5 border border-d8x-warning/15 rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium ${SEVERITY_BADGE[c.severity] ?? SEVERITY_BADGE.medium}`}>
                    {c.severity}
                  </span>
                  <p className="text-sm">{c.description}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${TYPE_BADGE[c.type] ?? TYPE_BADGE.ambiguity}`}>
                    {(c.type ?? "").replace(/_/g, " ")}
                  </span>
                  {c.location && (
                    <span className="text-[10px] text-d8x-text-tertiary flex items-center gap-1">
                      <MapPin className="w-3 h-3" /> {c.location}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section 4: Data Conflicts & Gaps ── */}
      {dataConflicts.length > 0 && (
        <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-d8x-blue" />
            Conflicts & gaps ({dataConflicts.length})
          </h3>
          <div className="space-y-2">
            {dataConflicts.map((c: any, i: number) => (
              <div key={i} className="bg-d8x-background border border-d8x-border rounded-lg p-3">
                <div className="flex items-start gap-2">
                  <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded font-medium ${SEVERITY_BADGE[c.severity] ?? SEVERITY_BADGE.medium}`}>
                    {c.severity}
                  </span>
                  <p className="text-sm">{c.description}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${TYPE_BADGE[c.type] ?? TYPE_BADGE.ambiguity}`}>
                    {(c.type ?? "").replace(/_/g, " ")}
                  </span>
                  {c.source_a && c.source_b && c.source_a !== c.source_b && (
                    <span className="text-[10px] text-d8x-text-tertiary">
                      {c.source_a} ↔ {c.source_b}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section 5: Business rules ── */}
      {rules.length > 0 && (
        <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-4">Business rules ({rules.length})</h3>
          <div className="border border-d8x-border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-d8x-background text-d8x-text-secondary text-left text-xs">
                  <th className="px-4 py-2.5 font-medium w-16">ID</th>
                  <th className="px-4 py-2.5 font-medium">Rule</th>
                  <th className="px-4 py-2.5 font-medium">Source</th>
                  <th className="px-4 py-2.5 font-medium text-center w-24">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {rules.map((r: any, i: number) => (
                  <tr key={i} className="border-t border-d8x-border group">
                    <td className="px-4 py-2.5 text-xs text-d8x-text-tertiary font-mono">{r.id ?? `BR-${String(i + 1).padStart(3, "0")}`}</td>
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-d8x-text-primary">{r.name}</p>
                      <p className="text-xs text-d8x-text-secondary mt-0.5 line-clamp-2">{r.description}</p>
                    </td>
                    <td className="px-4 py-2.5 text-xs text-d8x-text-secondary max-w-[150px] truncate">{r.source ?? "—"}</td>
                    <td className="px-4 py-2.5 text-center">
                      <span className={`text-xs px-2 py-0.5 rounded ${CONF_BADGE[r.confidence] ?? CONF_BADGE.medium}`}>{r.confidence ?? "medium"}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── Section 6: Domain entities ── */}
      {entities.length > 0 && (
        <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-4">Domain model ({entities.length} entities)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {entities.map((e: any, i: number) => (
              <div key={i} className="bg-d8x-background border border-d8x-border rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-semibold text-sm">{e.name}</span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded ${ENTITY_TYPE_BADGE[e.type] ?? ENTITY_TYPE_BADGE.data_object}`}>{e.type}</span>
                </div>
                {e.attributes && (
                  <div className="flex flex-wrap gap-1 mb-2">
                    {(e.attributes as string[]).slice(0, 8).map((a: any, j: number) => (
                      <span key={j} className="text-[10px] px-1.5 py-0.5 rounded bg-d8x-border text-d8x-text-secondary">{typeof a === "string" ? a : a.name ?? a}</span>
                    ))}
                    {(e.attributes as any[]).length > 8 && <span className="text-[10px] text-d8x-text-tertiary">+{(e.attributes as any[]).length - 8} more</span>}
                  </div>
                )}
                {e.relationships && (e.relationships as string[]).slice(0, 3).map((r: any, j: number) => (
                  <p key={j} className="text-[11px] text-d8x-text-secondary flex items-center gap-1">
                    <ArrowRight className="w-3 h-3 text-d8x-text-tertiary" /> {typeof r === "string" ? r : `${r.relationship_type ?? ""} ${r.related_entity ?? r}`}
                  </p>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section 7: Questions for review ── */}
      {questions.length > 0 && (
        <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <MessageCircleQuestion className="w-4 h-4 text-d8x-blue" /> Questions for review ({questions.length})
          </h3>
          <div className="space-y-2">
            {questions.map((q: any, i: number) => (
              <div key={i} className="bg-d8x-background border border-d8x-border rounded-lg p-3">
                <p className="text-sm font-medium">{q.question}</p>
                {q.impact && <p className="text-xs text-d8x-text-secondary mt-1">Impact: {q.impact}</p>}
                <span className={`inline-block mt-1.5 text-[10px] px-1.5 py-0.5 rounded ${q.priority === "blocking" ? "bg-red-600/20 text-red-400" : q.priority === "high" ? "bg-red-500/15 text-red-400" : "bg-amber-500/15 text-amber-400"}`}>
                  {q.priority ?? "medium"} priority
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section 8: System understanding ── */}
      {understanding.purpose && (
        <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2"><BookOpen className="w-4 h-4 text-d8x-blue" /> System understanding</h3>
          <p className="text-sm text-d8x-text-secondary mb-3">{understanding.purpose}</p>
          {understanding.domain && <span className="text-[10px] px-2 py-0.5 rounded bg-d8x-blue/15 text-d8x-blue">{understanding.domain}</span>}
          {understanding.key_workflows && (
            <ol className="mt-3 space-y-1.5 list-decimal list-inside">
              {(understanding.key_workflows as string[]).map((w: string, i: number) => (
                <li key={i} className="text-xs text-d8x-text-secondary">{w}</li>
              ))}
            </ol>
          )}
          {understanding.critical_risks && (
            <div className="mt-3">
              <p className="text-xs font-medium text-d8x-text-secondary mb-1">Critical risks:</p>
              {(understanding.critical_risks as string[]).map((r: string, i: number) => (
                <p key={i} className="text-xs text-red-400/80 flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" /> {r}
                </p>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Section 9: Quality assessment ── */}
      {Object.keys(qa).length > 0 && (
        <div className="bg-d8x-surface border border-d8x-border rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-4">Quality assessment</h3>
          <div className="space-y-3">
            {(["completeness", "depth", "consistency", "traceability", "actionability", "security"] as const).map((dim) => {
              const val = (qa[dim] ?? 0) as number;
              if (val === 0 && dim === "security") return null;
              return (
                <div key={dim} className="flex items-center gap-3">
                  <span className="text-xs text-d8x-text-secondary w-28 capitalize">{dim}</span>
                  <div className="flex-1 h-2 bg-d8x-border rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${val >= 80 ? "bg-d8x-success" : val >= 60 ? "bg-d8x-warning" : "bg-d8x-danger"}`} style={{ width: `${Math.min(val, 100)}%` }} />
                  </div>
                  <span className="text-xs text-d8x-text-secondary w-12 text-right">{val}/100</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
