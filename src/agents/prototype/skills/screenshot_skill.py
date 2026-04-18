"""ScreenshotSkill: captures screenshots of prototype pages."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from pydantic import BaseModel, Field

from src.agents.base.skill import BaseSkill

logger = logging.getLogger(__name__)


class Screenshot(BaseModel):
    page: str = ""
    desktop_image_path: str = ""
    mobile_image_path: str = ""


class ScreenshotInput(BaseModel):
    preview_url: str
    pages: list[str] = Field(default_factory=list)  # route paths to capture


class ScreenshotSet(BaseModel):
    screenshots: list[Screenshot] = Field(default_factory=list)
    base_url: str = ""
    captured_at: str = ""


class ScreenshotSkill(BaseSkill[ScreenshotInput, ScreenshotSet]):
    """Captures desktop and mobile screenshots of prototype pages using Playwright."""

    name = "screenshot"
    description = "Capture desktop (1440px) and mobile (375px) screenshots of prototype pages"
    input_model = ScreenshotInput
    output_model = ScreenshotSet

    async def execute(self, input_data: ScreenshotInput) -> ScreenshotSet:
        from datetime import datetime, timezone

        screenshots: list[Screenshot] = []
        base_url = input_data.preview_url.rstrip("/")
        pages = input_data.pages or ["/"]

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.warning("playwright not installed — returning empty screenshots")
            return ScreenshotSet(
                screenshots=[Screenshot(page=p) for p in pages],
                base_url=base_url,
                captured_at=datetime.now(timezone.utc).isoformat(),
            )

        tmp_dir = tempfile.mkdtemp(prefix="d8x-screenshots-")

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)

                for page_path in pages:
                    url = f"{base_url}{page_path}"
                    safe_name = page_path.strip("/").replace("/", "_") or "index"

                    # Desktop screenshot (1440px)
                    desktop_path = str(Path(tmp_dir) / f"{safe_name}_desktop.png")
                    desktop_page = await browser.new_page(viewport={"width": 1440, "height": 900})
                    try:
                        await desktop_page.goto(url, wait_until="networkidle", timeout=15000)
                        await desktop_page.screenshot(path=desktop_path, full_page=True)
                    except Exception as e:
                        logger.warning("Failed to capture desktop screenshot for %s: %s", url, e)
                        desktop_path = ""
                    finally:
                        await desktop_page.close()

                    # Mobile screenshot (375px)
                    mobile_path = str(Path(tmp_dir) / f"{safe_name}_mobile.png")
                    mobile_page = await browser.new_page(viewport={"width": 375, "height": 812})
                    try:
                        await mobile_page.goto(url, wait_until="networkidle", timeout=15000)
                        await mobile_page.screenshot(path=mobile_path, full_page=True)
                    except Exception as e:
                        logger.warning("Failed to capture mobile screenshot for %s: %s", url, e)
                        mobile_path = ""
                    finally:
                        await mobile_page.close()

                    screenshots.append(Screenshot(
                        page=page_path,
                        desktop_image_path=desktop_path,
                        mobile_image_path=mobile_path,
                    ))

                await browser.close()

        except Exception as e:
            logger.error("Screenshot capture failed: %s", e)
            screenshots = [Screenshot(page=p) for p in pages]

        return ScreenshotSet(
            screenshots=screenshots,
            base_url=base_url,
            captured_at=datetime.now(timezone.utc).isoformat(),
        )
