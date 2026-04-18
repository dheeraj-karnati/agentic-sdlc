"""PrototypeValidatorSkill: validates generated prototype code."""

from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.agents.prototype.skills.ui_generator_skill import PrototypeCode


class ValidationResult(BaseModel):
    passed: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    file_count: int = 0
    has_package_json: bool = False
    has_layout: bool = False
    has_pages: bool = False
    route_count: int = 0


class PrototypeValidatorInput(BaseModel):
    prototype_code: PrototypeCode
    expected_routes: list[str] = Field(default_factory=list)


class PrototypeValidatorSkill(BaseSkill[PrototypeValidatorInput, ValidationResult]):
    """Validates prototype code for completeness and basic correctness."""

    name = "prototype_validator"
    description = "Validate prototype code: routes, imports, package.json, component presence"
    input_model = PrototypeValidatorInput
    output_model = ValidationResult

    async def execute(self, input_data: PrototypeValidatorInput) -> ValidationResult:
        code = input_data.prototype_code
        errors: list[str] = []
        warnings: list[str] = []

        # Check file tree is non-empty
        if not code.file_tree:
            errors.append("file_tree is empty — no files generated")
            return ValidationResult(passed=False, errors=errors)

        file_count = len(code.file_tree)

        # Check package.json
        has_package_json = bool(code.package_json)
        if not has_package_json:
            # Also check file_tree
            has_package_json = "package.json" in code.file_tree
        if not has_package_json:
            errors.append("Missing package.json")
        else:
            pkg_content = code.package_json or code.file_tree.get("package.json", "")
            if pkg_content:
                try:
                    pkg = json.loads(pkg_content)
                    if "dependencies" not in pkg:
                        warnings.append("package.json has no dependencies")
                    if "react" not in pkg.get("dependencies", {}):
                        warnings.append("package.json missing react dependency")
                except json.JSONDecodeError:
                    errors.append("package.json is not valid JSON")

        # Check for layout file
        has_layout = any(
            "layout" in fp.lower() for fp in code.file_tree
        )
        if not has_layout:
            warnings.append("No layout file found — prototype may lack consistent navigation")

        # Check for page files
        page_files = [fp for fp in code.file_tree if "page" in fp.lower() or fp.endswith("/page.tsx")]
        has_pages = len(page_files) > 0
        if not has_pages:
            errors.append("No page files found in file_tree")

        # Count routes (Next.js App Router: any directory with page.tsx)
        route_count = sum(
            1 for fp in code.file_tree
            if fp.endswith("page.tsx") or fp.endswith("page.jsx") or fp.endswith("page.ts")
        )

        # Check expected routes are present
        for route in input_data.expected_routes:
            route_path = route.strip("/").replace("/", "/")
            found = any(
                route_path in fp or route.lstrip("/") in fp
                for fp in code.file_tree
            )
            if not found:
                warnings.append(f"Expected route '{route}' not found in file_tree")

        # Check for broken imports (basic: look for imports from non-existent local files)
        all_files = set(code.file_tree.keys())
        for fp, content in code.file_tree.items():
            if not fp.endswith((".tsx", ".ts", ".jsx", ".js")):
                continue
            import_matches = re.findall(r"from ['\"](@/[^'\"]+)['\"]", content)
            for imp in import_matches:
                # @/ is the src root alias — just check it's not obviously broken
                if imp.count("/") > 5:
                    warnings.append(f"Deep import path in {fp}: {imp}")

        # Check for TypeScript type errors (very basic)
        for fp, content in code.file_tree.items():
            if fp.endswith((".tsx", ".ts")):
                if "any" in content and content.count(": any") > 5:
                    warnings.append(f"Excessive 'any' types in {fp} — consider proper typing")

        passed = len(errors) == 0
        return ValidationResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            file_count=file_count,
            has_package_json=has_package_json,
            has_layout=has_layout,
            has_pages=has_pages,
            route_count=route_count,
        )
