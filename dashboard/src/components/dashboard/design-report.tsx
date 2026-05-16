"use client";

import { Server, Database, Globe, Shield, Layout, CheckCircle2, FileCode, Layers, ArrowRight, Box } from "lucide-react";
import { QualityScore } from "./quality-score";

/* eslint-disable @typescript-eslint/no-explicit-any */

export function DesignReport({ output }: { output: Record<string, any> }) {
  const arch = output.architecture ?? {};
  const schema = output.database_schema ?? {};
  const api = output.api_specification ?? {};
  const auth = output.auth_design ?? {};
  const frontend = output.frontend_design ?? {};
  const qa = output.quality_assessment ?? {};
  const score = qa.score ?? 0;
  const adrs = (arch.adrs ?? []) as any[];
  const stack = (arch.stack ?? []) as any[];
  const tables = (schema.tables ?? []) as any[];
  const endpoints = (api.endpoints ?? []) as any[];

  return (
    <div className="space-y-5">
      {/* ── Section 1: Summary banner ── */}
      <div className="border-l-4 border-emerald-500 bg-ink-900 rounded-r-lg p-5 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">Design complete</h2>
          <p className="text-sm text-ink-300 mt-1">
            {arch.pattern?.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())} architecture
            with {schema.total_tables ?? tables.length} tables, {api.total_endpoints ?? endpoints.length} endpoints,
            and {auth.roles ?? 0} user roles.
          </p>
        </div>
        {score > 0 && <QualityScore score={score} size={72} />}
      </div>

      {/* ── Section 2: Architecture ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Server className="w-4 h-4 text-sky-500" />
          <h3 className="text-sm font-semibold">Architecture</h3>
          <span className="text-xs px-2 py-0.5 rounded bg-sky-500/15 text-sky-500 ml-2">
            {arch.pattern?.replace(/_/g, " ")}
          </span>
        </div>

        {arch.rationale && (
          <p className="text-sm text-ink-300 mb-4">{arch.rationale}</p>
        )}

        {/* Tech stack grid */}
        {stack.length > 0 && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-4">
            {stack.map((s: any, i: number) => (
              <div key={i} className="bg-ink-950 border border-ink-700 rounded-lg p-3">
                <span className="text-[10px] text-ink-400 uppercase tracking-wider">{s.category}</span>
                <p className="text-sm font-medium mt-0.5">{s.technology}</p>
              </div>
            ))}
          </div>
        )}

        {/* Dynamic architecture diagram */}
        <div className="bg-ink-950 border border-ink-700 rounded-lg p-4 mt-3">
          <p className="text-[10px] text-ink-400 uppercase tracking-wider mb-3">System Architecture</p>
          <div className="flex items-center justify-center gap-2 flex-wrap">
            <ArchNode label="Client" sub={stack.find((s: any) => s.category === "frontend")?.technology?.split(" ")[0] ?? "Frontend"} icon={Layout} color="text-blue-400" />
            <ArrowRight className="w-4 h-4 text-ink-400" />
            <ArchNode label="API Gateway" sub={stack.find((s: any) => s.category === "api_style")?.technology?.split(" ")[0] ?? "API"} icon={Shield} color="text-amber-400" />
            <ArrowRight className="w-4 h-4 text-ink-400" />
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-1.5 px-2 py-1 bg-sky-500/10 border border-sky-500/20 rounded text-xs text-sky-500">
                <Box className="w-3 h-3" />{stack.find((s: any) => s.category === "backend")?.technology?.split(" ")[0] ?? "Backend"}
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-ink-400" />
            <div className="flex flex-col gap-1">
              <ArchNode label={stack.find((s: any) => s.category === "database")?.technology?.split(" ")[0] ?? "Database"} sub="Primary DB" icon={Database} color="text-green-400" small />
              <ArchNode label={stack.find((s: any) => s.category === "cache")?.technology?.split(" ")[0] ?? "Cache"} sub="Cache" icon={Layers} color="text-red-400" small />
              <ArchNode label={stack.find((s: any) => s.category === "storage")?.technology?.split(" ")[0] ?? "Storage"} sub="Files" icon={FileCode} color="text-orange-400" small />
            </div>
          </div>
        </div>
      </div>

      {/* ── Section 3: ADRs ── */}
      {adrs.length > 0 && (
        <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-4">Architecture Decision Records ({adrs.length})</h3>
          <div className="space-y-2">
            {adrs.map((adr: any, i: number) => (
              <div key={i} className="flex items-start gap-3 bg-ink-950 border border-ink-700 rounded-lg p-3">
                <span className="text-[10px] font-mono text-ink-400 bg-ink-700 px-1.5 py-0.5 rounded shrink-0 mt-0.5">{adr.id}</span>
                <div className="min-w-0">
                  <p className="text-sm font-medium">{adr.title}</p>
                  <p className="text-xs text-ink-300 mt-0.5">{adr.decision}</p>
                  {adr.alternatives_considered && (adr.alternatives_considered as string[]).length > 0 && (
                    <div className="mt-1.5 pl-2 border-l-2 border-ink-700">
                      {(adr.alternatives_considered as string[]).map((alt: string, j: number) => (
                        <p key={j} className="text-[11px] text-ink-400">✗ {alt}</p>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Section 4: Database Schema ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Database className="w-4 h-4 text-green-400" />
          <h3 className="text-sm font-semibold">Database Schema ({schema.total_tables ?? tables.length} tables)</h3>
        </div>

        {/* ER diagram (visual) */}
        <div className="bg-ink-950 border border-ink-700 rounded-lg p-4 mb-4">
          <p className="text-[10px] text-ink-400 uppercase tracking-wider mb-3">Entity-Relationship Diagram</p>
          <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {tables.map((t: any, i: number) => (
              <div key={i} className="bg-ink-900 border border-ink-700 rounded p-2 text-center hover:border-green-500/30 transition-colors">
                <Database className="w-3 h-3 text-green-400 mx-auto mb-1" />
                <p className="text-[11px] font-medium truncate">{t.name}</p>
                <p className="text-[10px] text-ink-400">{t.columns} cols</p>
              </div>
            ))}
          </div>
        </div>

        {/* Table details */}
        <div className="border border-ink-700 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-ink-950 text-ink-300 text-left text-xs">
                <th className="px-4 py-2.5 font-medium">Table</th>
                <th className="px-4 py-2.5 font-medium text-center">Columns</th>
                <th className="px-4 py-2.5 font-medium">Purpose</th>
              </tr>
            </thead>
            <tbody>
              {tables.slice(0, 12).map((t: any, i: number) => (
                <tr key={i} className="border-t border-ink-700">
                  <td className="px-4 py-2 font-mono text-xs text-green-400">{t.name}</td>
                  <td className="px-4 py-2 text-center text-xs text-ink-300">{t.columns}</td>
                  <td className="px-4 py-2 text-xs text-ink-300">{t.purpose}</td>
                </tr>
              ))}
              {tables.length > 12 && (
                <tr className="border-t border-ink-700">
                  <td colSpan={3} className="px-4 py-2 text-xs text-ink-400 text-center">
                    + {tables.length - 12} more tables
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Section 5: API Specification ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Globe className="w-4 h-4 text-purple-400" />
          <h3 className="text-sm font-semibold">API Specification ({api.total_endpoints ?? endpoints.length} endpoints)</h3>
        </div>

        {endpoints.length > 0 && (
          <div className="border border-ink-700 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-ink-950 text-ink-300 text-left text-xs">
                  <th className="px-4 py-2.5 font-medium w-20">Method</th>
                  <th className="px-4 py-2.5 font-medium">Path</th>
                  {endpoints[0]?.domain && <th className="px-4 py-2.5 font-medium">Domain</th>}
                </tr>
              </thead>
              <tbody>
                {endpoints.slice(0, 15).map((ep: any, i: number) => (
                  <tr key={i} className="border-t border-ink-700">
                    <td className="px-4 py-2">
                      <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                        ep.method === "GET" ? "bg-green-500/15 text-green-400" :
                        ep.method === "POST" ? "bg-blue-500/15 text-blue-400" :
                        ep.method === "PUT" || ep.method === "PATCH" ? "bg-amber-500/15 text-amber-400" :
                        "bg-red-500/15 text-red-400"
                      }`}>{ep.method}</span>
                    </td>
                    <td className="px-4 py-2 font-mono text-xs">{ep.path}</td>
                    {ep.domain && <td className="px-4 py-2 text-xs text-ink-300">{ep.domain}</td>}
                  </tr>
                ))}
                {endpoints.length > 15 && (
                  <tr className="border-t border-ink-700">
                    <td colSpan={3} className="px-4 py-2 text-xs text-ink-400 text-center">
                      + {endpoints.length - 15} more endpoints
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── Section 6: Auth Design ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-semibold">Authentication & Authorization</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">Strategy</span>
            <p className="text-sm font-medium mt-0.5">{auth.strategy ?? "JWT"}</p>
          </div>
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">Roles</span>
            <p className="text-sm font-medium mt-0.5">{auth.roles ?? 0}</p>
          </div>
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">Permissions</span>
            <p className="text-sm font-medium mt-0.5">{auth.permissions ?? 0}</p>
          </div>
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">MFA</span>
            <p className="text-sm font-medium mt-0.5">{auth.mfa ?? "Required"}</p>
          </div>
        </div>
      </div>

      {/* ── Section 7: Frontend Design ── */}
      <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
        <div className="flex items-center gap-2 mb-4">
          <Layout className="w-4 h-4 text-blue-400" />
          <h3 className="text-sm font-semibold">Frontend Design</h3>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">Framework</span>
            <p className="text-sm font-medium mt-0.5">{frontend.framework ?? "Next.js"}</p>
          </div>
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">Pages</span>
            <p className="text-sm font-medium mt-0.5">{frontend.pages ?? 0}</p>
          </div>
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">Components</span>
            <p className="text-sm font-medium mt-0.5">{frontend.components ?? 0}</p>
          </div>
          <div className="bg-ink-950 border border-ink-700 rounded-lg p-3">
            <span className="text-[10px] text-ink-400">State Management</span>
            <p className="text-sm font-medium mt-0.5">{frontend.state_management ?? "React Query"}</p>
          </div>
        </div>
      </div>

      {/* ── Section 8: Quality Assessment ── */}
      {Object.keys(qa).length > 0 && (
        <div className="bg-ink-900 border border-ink-700 rounded-lg p-5">
          <h3 className="text-sm font-semibold mb-4">Design Quality Assessment</h3>
          <div className="space-y-3">
            {(["completeness", "consistency", "feasibility", "traceability", "security"] as const).map((dim) => {
              const val = (qa[dim] ?? 0) as number;
              return (
                <div key={dim} className="flex items-center gap-3">
                  <span className="text-xs text-ink-300 w-28 capitalize">{dim}</span>
                  <div className="flex-1 h-2 bg-ink-700 rounded-full overflow-hidden">
                    <div className={`h-full rounded-full ${val >= 80 ? "bg-emerald-500" : val >= 60 ? "bg-amber-500" : "bg-red-500"}`} style={{ width: `${Math.min(val, 100)}%` }} />
                  </div>
                  <span className="text-xs text-ink-300 w-12 text-right">{val}/100</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

function ArchNode({ label, sub, icon: Icon, color, small }: { label: string; sub: string; icon: typeof Server; color: string; small?: boolean }) {
  return (
    <div className={`flex flex-col items-center gap-1 ${small ? "px-2 py-1.5" : "px-3 py-2"} bg-ink-900 border border-ink-700 rounded-lg`}>
      <Icon className={`${small ? "w-3 h-3" : "w-4 h-4"} ${color}`} />
      <span className={`${small ? "text-[10px]" : "text-xs"} font-medium`}>{label}</span>
      <span className="text-[9px] text-ink-400">{sub}</span>
    </div>
  );
}
