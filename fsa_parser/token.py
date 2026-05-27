from __future__ import annotations

import asyncio

from playwright.async_api import async_playwright


class TokenManager:
    def __init__(self, initial_token: str | None = None, timeout_ms: int = 45_000) -> None:
        self._token = initial_token or ""
        self._timeout_ms = timeout_ms
        self._lock = asyncio.Lock()

    async def get_token(self) -> str:
        if self._token:
            return self._token
        return await self.refresh()

    async def refresh(self, force: bool = False) -> str:
        async with self._lock:
            if self._token and not force:
                return self._token

            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    page = await browser.new_page()
                    await page.goto(
                        "https://pub.fsa.gov.ru/rss/certificate",
                        wait_until="domcontentloaded",
                        timeout=self._timeout_ms,
                    )
                    await page.wait_for_function(
                        "() => Boolean(localStorage.getItem('fgis_token'))",
                        timeout=self._timeout_ms,
                    )
                    token = await page.evaluate("() => localStorage.getItem('fgis_token')")
                finally:
                    await browser.close()

            if not token:
                raise RuntimeError("Could not obtain anonymous fgis_token")
            self._token = token
            return token

    def clear(self) -> None:
        self._token = ""
