"""UIGeneratorSkill: generates a complete Next.js/React prototype application."""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.agents.prototype.skills.design_interpreter_skill import PrototypeSpec
from src.tools.json_utils import parse_llm_json
from src.tools.llm import get_llm


class PrototypeCode(BaseModel):
    file_tree: dict[str, str] = Field(default_factory=dict)  # filepath → content
    package_json: str = ""
    readme: str = ""
    total_files: int = 0
    framework: str = "nextjs"


class UIGeneratorInput(BaseModel):
    prototype_spec: PrototypeSpec
    feedback_history: list[dict[str, Any]] = Field(default_factory=list)
    business_context_summary: str = ""


_SYSTEM_PROMPT = """\
You are a senior React/Next.js developer generating a complete, production-quality \
prototype application.

Generate a Next.js 14+ App Router application with:
- App layout with sidebar or topbar navigation (based on the spec)
- Pages for each route with functional React components
- Mock data matching the DB schema (realistic domain-specific data)
- API mock layer using Next.js API routes or local JSON
- Role-based view differences (admin sees management UI, viewer sees read-only)
- Responsive layout (mobile + desktop) using Tailwind CSS
- shadcn/ui components for professional appearance
- Form validation matching business rules
- Loading states, empty states, error states
- TypeScript throughout

## Example: Shallow vs Production Prototype

BAD (shallow):
```tsx
export default function Dashboard() {
  return <div>Dashboard Page</div>
}
```

GOOD (production):
```tsx
'use client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable } from '@/components/data-table'
import { useQuery } from '@tanstack/react-query'

export default function DashboardPage() {
  const { data: stats, isLoading } = useQuery({ queryKey: ['stats'], queryFn: fetchStats })

  if (isLoading) return <DashboardSkeleton />

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Total Orders" value={stats.orderCount} trend="+12%" />
        <StatCard title="Revenue" value={formatCurrency(stats.revenue)} trend="+8%" />
        ...
      </div>
      <DataTable columns={orderColumns} data={stats.recentOrders} />
    </div>
  )
}
```

If feedback_history is present, incorporate ALL previous feedback cumulatively. \
Do NOT regenerate from scratch — modify the existing code.

Return JSON with:
- file_tree: dict mapping file paths to file contents (e.g., "src/app/page.tsx": "...")
- package_json: complete package.json content
- readme: setup instructions
- total_files: count of files in file_tree
- framework: "nextjs"
"""


class UIGeneratorSkill(BaseSkill[UIGeneratorInput, PrototypeCode]):
    """Generates a complete Next.js/React prototype application."""

    name = "ui_generator"
    description = "Generate complete Next.js prototype with pages, components, mock data, and styling"
    input_model = UIGeneratorInput
    output_model = PrototypeCode

    def __init__(self, llm: Any | None = None) -> None:
        self._llm = llm

    async def execute(self, input_data: UIGeneratorInput) -> PrototypeCode:
        llm = self._llm or get_llm(max_tokens=16384)

        schema_json = json.dumps(PrototypeCode.model_json_schema(), indent=2)
        system = f"{_SYSTEM_PROMPT}\n\nOutput schema:\n```json\n{schema_json}\n```"

        parts = [f"## Prototype Spec\n{json.dumps(input_data.prototype_spec.model_dump(mode='json'), indent=2)}"]

        if input_data.business_context_summary:
            parts.append(f"\n## Business Context\n{input_data.business_context_summary}")

        if input_data.feedback_history:
            parts.append("\n## Feedback History (incorporate ALL cumulatively)")
            for i, fb in enumerate(input_data.feedback_history, 1):
                parts.append(f"\nRound {i}: {json.dumps(fb, default=str)}")

        response = await llm.ainvoke([
            SystemMessage(content=system),
            HumanMessage(content="\n".join(parts)),
        ])

        parsed = parse_llm_json(response.content)  # type: ignore[arg-type]
        result = PrototypeCode.model_validate(parsed)
        result.total_files = len(result.file_tree)
        return result
