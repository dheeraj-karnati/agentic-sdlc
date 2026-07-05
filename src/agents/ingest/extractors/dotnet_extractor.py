"""Deep C# / .NET / ASP.NET code structure extractor.

Extracts controllers, Entity Framework models, WCF services,
dependency injection, middleware, MediatR, FluentValidation patterns.
"""

from __future__ import annotations

import logging
import re

from src.agents.ingest.skills.code_structure_skill import (
    CodeStructure,
    HardcodedValue,
    MethodSignature,
)

logger = logging.getLogger(__name__)


def extract(content: str, file_path: str) -> CodeStructure:
    """Extract structure from C# / .NET source."""
    cs = CodeStructure(language="csharp", file_path=file_path)

    # ─── Namespace ───
    m = re.search(r"namespace\s+([\w.]+)", content)
    if m:
        cs.package = m.group(1)

    # ─── Using imports ───
    cs.imports = re.findall(r"using\s+([\w.]+)\s*;", content)

    # ─── Class declaration ───
    m = re.search(
        r"(?:public|internal|private|protected)?\s*(?:abstract\s+|sealed\s+|static\s+|partial\s+)*"
        r"class\s+(\w+)(?:<[^>]+>)?\s*(?::\s*([\w\s,.<>]+))?",
        content,
    )
    if m:
        cs.class_name = m.group(1)
        if m.group(2):
            bases = [b.strip() for b in m.group(2).split(",")]
            if bases:
                cs.parent_class = bases[0]
                cs.interfaces = bases[1:]

    # ─── Interface declaration ───
    if not cs.class_name:
        m = re.search(r"(?:public|internal)?\s*interface\s+(\w+)(?:<[^>]+>)?\s*(?::\s*([\w\s,.<>]+))?", content)
        if m:
            cs.class_name = m.group(1)

    # ─── Enum declaration ───
    enum_match = re.search(r"(?:public|internal)?\s*enum\s+(\w+)\s*\{([^}]+)\}", content)
    if enum_match and not cs.class_name:
        cs.class_name = enum_match.group(1)
        values = [v.strip().split("=")[0].strip() for v in enum_match.group(2).split(",") if v.strip()]
        cs.key_comments.append(f"ENUM: {enum_match.group(1)} = {', '.join(values[:10])}")

    # ─── Class-level attributes ───
    class_attrs = re.findall(r"\[(\w+)(?:\([^]]*\))?\]\s*(?:public|internal|private|abstract|sealed|partial|class|interface)", content)
    cs.annotations = list(dict.fromkeys(class_attrs))

    # ─── Methods ───
    method_pattern = re.compile(
        r"(?:\[(\w+)(?:\([^]]*\))?\]\s*)*"
        r"(?:public|protected|private|internal)\s+"
        r"(?:static\s+)?(?:async\s+)?(?:virtual\s+)?(?:override\s+)?(?:abstract\s+)?"
        r"([\w<>\[\]?,\s]+?)\s+(\w+)\s*\(([^)]*)\)",
    )
    for match in method_pattern.finditer(content):
        attr = match.group(1)
        ret = match.group(2).strip()
        name = match.group(3)
        params = match.group(4).strip()
        ms = MethodSignature(name=name, params=params, return_type=ret)
        if attr:
            ms.annotations = [attr]
        cs.methods.append(ms)

    # ─── ASP.NET Controller endpoints ───
    for m in re.finditer(r'\[(?:Http(?:Get|Post|Put|Delete|Patch))\s*(?:\("([^"]*)")?\s*\]', content):
        path = m.group(1) or ""
        cs.entry_points.append(f"Endpoint: {path}")

    for m in re.finditer(r'\[Route\s*\("([^"]+)"\)\]', content):
        cs.entry_points.append(f"Route: {m.group(1)}")

    # ─── Entity Framework: DbContext / DbSet ───
    for m in re.finditer(r"DbSet<(\w+)>", content):
        cs.dependencies.append(f"ENTITY: {m.group(1)}")

    if re.search(r":\s*DbContext", content):
        cs.key_comments.append("EF DbContext — database access layer")

    # ─── Entity Framework: Table/Column attributes ───
    for m in re.finditer(r'\[Table\s*\("(\w+)"\)\]', content):
        cs.key_comments.append(f"DB TABLE: {m.group(1)}")
    # Column attributes and LINQ queries detected but too granular for summary

    # ─── WCF: ServiceContract / OperationContract ───
    if re.search(r"\[ServiceContract\]", content):
        cs.annotations.append("WCF_ServiceContract")
    for m in re.finditer(r"\[OperationContract\].*?(?:public|private)\s+\w+\s+(\w+)\s*\(", content, re.DOTALL):
        cs.entry_points.append(f"WCF: {m.group(1)}")

    # ─── SignalR ───
    if re.search(r":\s*Hub\b", content):
        cs.annotations.append("SignalR_Hub")

    # ─── Background services ───
    if re.search(r":\s*(?:BackgroundService|IHostedService)", content):
        cs.annotations.append("BackgroundService")
        cs.entry_points.append("Background worker")

    # ─── DI registrations ───
    for m in re.finditer(r"services\.Add(?:Scoped|Transient|Singleton)<(\w+)(?:,\s*(\w+))?>", content):
        interface = m.group(1)
        impl = m.group(2) or interface
        cs.dependencies.append(f"DI: {interface} -> {impl}")

    # ─── Middleware ───
    for m in re.finditer(r"app\.Use(\w+)\s*\(", content):
        cs.key_comments.append(f"MIDDLEWARE: {m.group(1)}")

    # ─── MediatR ───
    if re.search(r"IRequestHandler|INotificationHandler|Mediator", content):
        cs.annotations.append("MediatR")
    for m in re.finditer(r":\s*IRequestHandler<(\w+)(?:,\s*(\w+))?>", content):
        cs.entry_points.append(f"CQRS Handler: {m.group(1)}")

    # ─── FluentValidation ───
    if re.search(r"AbstractValidator|IRuleBuilder", content):
        cs.annotations.append("FluentValidation")
    for m in re.finditer(r"RuleFor\s*\(\s*\w+\s*=>\s*\w+\.(\w+)\)", content):
        cs.key_comments.append(f"VALIDATION: {m.group(1)}")

    # ─── AutoMapper ───
    if re.search(r"Profile|CreateMap|ForMember", content):
        for m in re.finditer(r"CreateMap<(\w+),\s*(\w+)>", content):
            cs.key_comments.append(f"MAPPING: {m.group(1)} -> {m.group(2)}")

    # ─── Security attributes ───
    for m in re.finditer(r'\[(?:Authorize|AllowAnonymous)\s*(?:\(Roles\s*=\s*"([^"]+)")?\]', content):
        roles = m.group(1) or "any"
        cs.key_comments.append(f"AUTH: Roles={roles}")

    # ─── SQL / Dapper ───
    for m in re.finditer(r'["\'](\s*(?:SELECT|INSERT|UPDATE|DELETE)\s[^"\']{10,})["\']', content, re.IGNORECASE):
        cs.sql_queries.append(m.group(1).strip()[:200])

    # ─── Constructor injection ───
    for m in re.finditer(r"(?:private|protected)\s+(?:readonly\s+)?(\w+)\s+_\w+;", content):
        dep = m.group(1)
        if dep[0].isupper() and dep not in ("String", "Int32", "Boolean", "Object"):
            cs.dependencies.append(dep)
    cs.dependencies = list(dict.fromkeys(cs.dependencies))

    # ─── Hardcoded values ───
    for m in re.finditer(r"(?:const|static\s+readonly)\s+\w+\s+(\w+)\s*=\s*(\d{3,}|\"[^\"]{5,50}\")", content):
        cs.hardcoded_values.append(HardcodedValue(name=m.group(1), value=m.group(2)))

    # ─── Key comments ───
    for m in re.finditer(r"//\s*(TODO|FIXME|HACK|XXX|BUSINESS\s*RULE)[:\s]*(.*)", content, re.IGNORECASE):
        cs.key_comments.append(f"{m.group(1)}: {m.group(2).strip()[:200]}")

    return cs
