"""PreviewDeploymentSkill: deploys prototype to a preview URL.

Supports multiple providers via a base PreviewProvider class:
- VercelProvider: Vercel auto-deploy via GitHub
- NetlifyProvider: Netlify CLI/API deploy
- S3StaticProvider: S3 + static export (works with MinIO, AWS, GCS)
- LocalDockerProvider: Docker container on local/remote host
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill
from src.agents.prototype.skills.ui_generator_skill import PrototypeCode

logger = logging.getLogger(__name__)


class DeploymentStatus(BaseModel):
    state: str = "unknown"  # deploying, ready, error, deleted
    url: str = ""
    error: str = ""


class PreviewDeployment(BaseModel):
    url: str = ""
    provider: str = ""
    deployment_id: str = ""
    created_at: str = ""
    status: str = "deploying"  # deploying, ready, error


class PreviewDeploymentInput(BaseModel):
    prototype_code: PrototypeCode
    provider: str = "local_docker"  # vercel, netlify, s3_static, local_docker
    project_name: str = "d8x-prototype"


# ─── Provider Base Class ───


class PreviewProvider(ABC):
    """Base class for preview deployment providers."""

    @abstractmethod
    async def deploy(self, code: PrototypeCode, project_name: str) -> PreviewDeployment:
        ...

    @abstractmethod
    async def teardown(self, deployment_id: str) -> bool:
        ...

    @abstractmethod
    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        ...


# ─── Vercel Provider ───


class VercelProvider(PreviewProvider):
    """Deploy to Vercel via API."""

    def __init__(self) -> None:
        self.token = os.environ.get("VERCEL_TOKEN", "")
        self.org_id = os.environ.get("VERCEL_ORG_ID", "")

    async def deploy(self, code: PrototypeCode, project_name: str) -> PreviewDeployment:
        if not self.token:
            raise RuntimeError("VERCEL_TOKEN not set")

        import httpx

        # Create deployment via Vercel API
        files = []
        for fp, content in code.file_tree.items():
            files.append({"file": fp, "data": content})
        if code.package_json:
            files.append({"file": "package.json", "data": code.package_json})

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.vercel.com/v13/deployments",
                headers={"Authorization": f"Bearer {self.token}"},
                json={
                    "name": project_name,
                    "files": files,
                    "projectSettings": {"framework": "nextjs"},
                },
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()

        return PreviewDeployment(
            url=f"https://{data.get('url', '')}",
            provider="vercel",
            deployment_id=data.get("id", ""),
            created_at=datetime.now(timezone.utc).isoformat(),
            status="deploying",
        )

    async def teardown(self, deployment_id: str) -> bool:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.delete(
                f"https://api.vercel.com/v13/deployments/{deployment_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
        return resp.status_code in (200, 204)

    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.vercel.com/v13/deployments/{deployment_id}",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            data = resp.json()
        state_map = {"READY": "ready", "ERROR": "error", "BUILDING": "deploying"}
        return DeploymentStatus(
            state=state_map.get(data.get("readyState", ""), "unknown"),
            url=f"https://{data.get('url', '')}",
        )


# ─── Netlify Provider ───


class NetlifyProvider(PreviewProvider):
    """Deploy to Netlify via API."""

    def __init__(self) -> None:
        self.token = os.environ.get("NETLIFY_AUTH_TOKEN", "")

    async def deploy(self, code: PrototypeCode, project_name: str) -> PreviewDeployment:
        if not self.token:
            raise RuntimeError("NETLIFY_AUTH_TOKEN not set")

        import httpx

        # Create site + deploy
        async with httpx.AsyncClient() as client:
            # Create site
            site_resp = await client.post(
                "https://api.netlify.com/api/v1/sites",
                headers={"Authorization": f"Bearer {self.token}"},
                json={"name": project_name},
                timeout=30,
            )
            site_data = site_resp.json()
            site_id = site_data.get("id", "")

            # Deploy files
            deploy_resp = await client.post(
                f"https://api.netlify.com/api/v1/sites/{site_id}/deploys",
                headers={"Authorization": f"Bearer {self.token}",
                         "Content-Type": "application/json"},
                json={"files": {fp: fp for fp in code.file_tree}},
                timeout=120,
            )
            deploy_data = deploy_resp.json()

        return PreviewDeployment(
            url=f"https://{site_data.get('subdomain', project_name)}.netlify.app",
            provider="netlify",
            deployment_id=deploy_data.get("id", site_id),
            created_at=datetime.now(timezone.utc).isoformat(),
            status="deploying",
        )

    async def teardown(self, deployment_id: str) -> bool:
        return True  # Netlify sites persist; would need site deletion

    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        return DeploymentStatus(state="ready")


# ─── S3 Static Provider ───


class S3StaticProvider(PreviewProvider):
    """Deploy as static export to S3-compatible storage."""

    async def deploy(self, code: PrototypeCode, project_name: str) -> PreviewDeployment:
        from src.services.storage import get_storage

        storage = get_storage()
        prefix = f"previews/{project_name}"

        # Write files to S3
        for fp, content in code.file_tree.items():
            s3_key = f"{prefix}/{fp}"
            content_type = "text/html" if fp.endswith(".html") else "application/javascript"
            if fp.endswith(".css"):
                content_type = "text/css"
            elif fp.endswith(".json"):
                content_type = "application/json"
            storage.upload_bytes(content.encode(), s3_key, content_type=content_type)

        # Create a simple index.html wrapper if none exists
        if "index.html" not in code.file_tree:
            index = "<html><body><h1>Prototype Preview</h1><p>Static export</p></body></html>"
            storage.upload_bytes(index.encode(), f"{prefix}/index.html", content_type="text/html")

        url = storage.generate_presigned_url(f"{prefix}/index.html", expires_in=86400)

        return PreviewDeployment(
            url=url,
            provider="s3_static",
            deployment_id=prefix,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="ready",
        )

    async def teardown(self, deployment_id: str) -> bool:
        return True

    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        return DeploymentStatus(state="ready")


# ─── Local Docker Provider ───


class LocalDockerProvider(PreviewProvider):
    """Deploy via Docker container on local or remote host."""

    def __init__(self) -> None:
        self.docker_host = os.environ.get("DOCKER_HOST", "")

    async def deploy(self, code: PrototypeCode, project_name: str) -> PreviewDeployment:
        import asyncio

        # Write files to temp directory
        tmp_dir = tempfile.mkdtemp(prefix="d8x-proto-")
        for fp, content in code.file_tree.items():
            file_path = Path(tmp_dir) / fp
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        if code.package_json:
            (Path(tmp_dir) / "package.json").write_text(code.package_json)

        # Create Dockerfile
        dockerfile = (
            "FROM node:20-alpine\n"
            "WORKDIR /app\n"
            "COPY package.json .\n"
            "RUN npm install\n"
            "COPY . .\n"
            "RUN npm run build 2>/dev/null || true\n"
            "EXPOSE 3000\n"
            "CMD [\"npm\", \"run\", \"dev\"]\n"
        )
        (Path(tmp_dir) / "Dockerfile").write_text(dockerfile)

        container_name = f"d8x-{project_name}"
        port = 3100  # Use a non-standard port to avoid conflicts

        try:
            # Build and run
            env = dict(os.environ)
            if self.docker_host:
                env["DOCKER_HOST"] = self.docker_host

            proc = await asyncio.create_subprocess_exec(
                "docker", "build", "-t", container_name, tmp_dir,
                env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Stop existing container if running
            proc = await asyncio.create_subprocess_exec(
                "docker", "rm", "-f", container_name,
                env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            # Run new container
            proc = await asyncio.create_subprocess_exec(
                "docker", "run", "-d", "--name", container_name,
                "-p", f"{port}:3000", container_name,
                env=env, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            container_id = stdout.decode().strip()[:12]

        except Exception as e:
            logger.error("Docker deployment failed: %s", e)
            return PreviewDeployment(
                provider="local_docker",
                deployment_id=container_name,
                status="error",
                created_at=datetime.now(timezone.utc).isoformat(),
            )

        host = self.docker_host.split("//")[-1].split(":")[0] if self.docker_host else "localhost"
        url = f"http://{host}:{port}"

        return PreviewDeployment(
            url=url,
            provider="local_docker",
            deployment_id=container_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            status="deploying",
        )

    async def teardown(self, deployment_id: str) -> bool:
        import asyncio

        proc = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", deployment_id,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        return proc.returncode == 0

    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        import asyncio

        proc = await asyncio.create_subprocess_exec(
            "docker", "inspect", "--format", "{{.State.Status}}", deployment_id,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        state = stdout.decode().strip()
        state_map = {"running": "ready", "created": "deploying", "exited": "error"}
        return DeploymentStatus(state=state_map.get(state, "unknown"))


# ─── Local Dev Provider (simplest — no Docker, no cloud) ───


class LocalDevProvider(PreviewProvider):
    """Write files to disk, npm install, npm run dev. Best for demos."""

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None  # type: ignore[type-arg]
        self._project_dir: str = ""

    async def deploy(self, code: PrototypeCode, project_name: str) -> PreviewDeployment:
        import asyncio
        import signal

        # Write files to a persistent directory (not /tmp — survives the demo)
        base_dir = Path.home() / ".d8x" / "previews"
        base_dir.mkdir(parents=True, exist_ok=True)
        project_dir = base_dir / project_name
        self._project_dir = str(project_dir)

        # Clean previous version
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
        project_dir.mkdir(parents=True)

        # Write all files from file_tree
        for fp, content in code.file_tree.items():
            file_path = project_dir / fp
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)

        # Write package.json
        if code.package_json:
            pkg_path = project_dir / "package.json"
            if not pkg_path.exists():
                pkg_path.write_text(code.package_json)

        # Write next.config.mjs if missing
        next_config = project_dir / "next.config.mjs"
        if not next_config.exists():
            next_config.write_text('/** @type {import("next").NextConfig} */\nconst config = {};\nexport default config;\n')

        # Write tsconfig.json if missing
        tsconfig = project_dir / "tsconfig.json"
        if not tsconfig.exists():
            tsconfig.write_text('{"compilerOptions":{"target":"ES2017","lib":["dom","dom.iterable","esnext"],"allowJs":true,"skipLibCheck":true,"strict":false,"noEmit":true,"esModuleInterop":true,"module":"esnext","moduleResolution":"bundler","resolveJsonModule":true,"isolatedModules":true,"jsx":"preserve","incremental":true,"plugins":[{"name":"next"}],"paths":{"@/*":["./src/*"]}},"include":["next-env.d.ts","**/*.ts","**/*.tsx",".next/types/**/*.ts"],"exclude":["node_modules"]}\n')

        # Write tailwind.config.ts if missing
        tw_config = project_dir / "tailwind.config.ts"
        if not tw_config.exists():
            tw_config.write_text('import type { Config } from "tailwindcss";\nconst config: Config = { content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"], theme: { extend: {} }, plugins: [] };\nexport default config;\n')

        # Write postcss.config.mjs if missing
        postcss = project_dir / "postcss.config.mjs"
        if not postcss.exists():
            postcss.write_text('const config = { plugins: { tailwindcss: {}, autoprefixer: {} } };\nexport default config;\n')

        # Write globals.css if missing
        globals_css = project_dir / "src" / "app" / "globals.css"
        if not globals_css.exists():
            globals_css.parent.mkdir(parents=True, exist_ok=True)
            globals_css.write_text("@tailwind base;\n@tailwind components;\n@tailwind utilities;\n")

        port = 3100
        logger.info("Prototype written to %s", project_dir)

        # npm install
        logger.info("Running npm install...")
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", "--legacy-peer-deps",
            cwd=str(project_dir),
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error("npm install failed: %s", stderr.decode()[-500:])
            return PreviewDeployment(
                url="", provider="local_dev", deployment_id=str(project_dir),
                created_at=datetime.now(timezone.utc).isoformat(), status="error",
            )

        # Start dev server in background
        logger.info("Starting Next.js dev server on port %d...", port)
        self._process = subprocess.Popen(
            ["npx", "next", "dev", "--port", str(port)],
            cwd=str(project_dir),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            preexec_fn=os.setsid if os.name != "nt" else None,
        )

        # Wait for server to be ready
        import httpx
        for _ in range(30):
            await asyncio.sleep(1)
            try:
                async with httpx.AsyncClient() as client:
                    resp = await client.get(f"http://localhost:{port}", timeout=2)
                    if resp.status_code < 500:
                        break
            except Exception:
                continue

        return PreviewDeployment(
            url=f"http://localhost:{port}",
            provider="local_dev",
            deployment_id=str(project_dir),
            created_at=datetime.now(timezone.utc).isoformat(),
            status="ready",
        )

    async def teardown(self, deployment_id: str) -> bool:
        if self._process:
            try:
                os.killpg(os.getpgid(self._process.pid), 9)
            except (ProcessLookupError, OSError):
                pass
            self._process = None
        return True

    async def get_status(self, deployment_id: str) -> DeploymentStatus:
        if self._process and self._process.poll() is None:
            return DeploymentStatus(state="ready")
        return DeploymentStatus(state="error")


# ─── Provider Registry ───

PROVIDERS: dict[str, type[PreviewProvider]] = {
    "vercel": VercelProvider,
    "netlify": NetlifyProvider,
    "s3_static": S3StaticProvider,
    "local_docker": LocalDockerProvider,
    "local_dev": LocalDevProvider,
}


def get_provider(name: str) -> PreviewProvider:
    """Get a preview deployment provider by name."""
    cls = PROVIDERS.get(name)
    if cls is None:
        raise ValueError(f"Unknown preview provider: {name}. Options: {list(PROVIDERS.keys())}")
    return cls()


# ─── Skill ───


class PreviewDeploymentSkill(BaseSkill[PreviewDeploymentInput, PreviewDeployment]):
    """Deploys prototype code to a preview URL using the configured provider."""

    name = "preview_deployment"
    description = "Deploy prototype to preview URL via Vercel, Netlify, S3, or Docker"
    input_model = PreviewDeploymentInput
    output_model = PreviewDeployment

    async def execute(self, input_data: PreviewDeploymentInput) -> PreviewDeployment:
        provider = get_provider(input_data.provider)
        return await provider.deploy(
            input_data.prototype_code,
            input_data.project_name,
        )
