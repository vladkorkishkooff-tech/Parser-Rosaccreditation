from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .models import LookupResult
from .normalization import normalize_number
from .token import TokenManager


BASE_URL = "https://pub.fsa.gov.ru"
CERTIFICATE_SEARCH_URL = f"{BASE_URL}/api/v1/rss/common/certificates/get"
DECLARATION_SEARCH_URL = f"{BASE_URL}/api/v1/rds/common/declarations/get"

STATUS_MAP = {
    "1": "Действует",
    "2": "Приостановлен",
    "3": "Прекращен",
    "4": "Аннулирован",
    "5": "Отменен",
    "6": "Архивный",
}


class FsaClient:
    def __init__(
        self,
        token_manager: TokenManager,
        timeout: float = 30.0,
        retries: int = 3,
    ) -> None:
        self._token_manager = token_manager
        self._timeout = timeout
        self._retries = retries
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def lookup(self, number: str) -> LookupResult:
        normalized = normalize_number(number)
        if not normalized:
            return LookupResult(input_number=number, registry_type="error", error="empty number")

        try:
            certificates = await self._search_certificates(normalized)
            certificate_result = self._select_result(normalized, certificates, "certificate")
            if certificate_result.registry_type != "not_found":
                return certificate_result

            declarations = await self._search_declarations(normalized)
            return self._select_result(normalized, declarations, "declaration")
        except Exception as exc:
            return LookupResult(input_number=normalized, registry_type="error", error=str(exc))

    async def get_latest_certificates(self, limit: int = 50) -> list[LookupResult]:
        payload = {
            "size": limit,
            "page": 0,
            "filter": {
                "idCertScheme": [],
                "regDate": {"startDate": None, "endDate": None},
                "endDate": {"startDate": None, "endDate": None},
                "columnsSearch": [],
            },
            "columnsSort": [{"column": "date", "sort": "DESC"}],
        }
        data = await self._post_json(CERTIFICATE_SEARCH_URL, payload, referer=f"{BASE_URL}/rss/certificate")
        items = data.get("items") or []

        results = []
        for item in items:
            item_id = str(item.get("id") or "")
            url = f"{BASE_URL}/rss/certificate/view/{item_id}/baseInfo"
            reg_date = item.get("date") or ""
            end_date = item.get("endDate") or ""
            status_id = str(item.get("idStatus") or "")
            status = STATUS_MAP.get(status_id, f"Неизвестный ({status_id})" if status_id else "")

            results.append(
                LookupResult(
                    input_number="",
                    registry_type="certificate",
                    registry_number=normalize_number(item.get("number")),
                    id=item_id,
                    url=url,
                    reg_date=str(reg_date or ""),
                    end_date=str(end_date or ""),
                    status_id=status_id,
                    status=status,
                )
            )
        return results

    async def get_latest_declarations(self, limit: int = 50) -> list[LookupResult]:
        payload = {
            "size": limit,
            "page": 0,
            "count": 0,
            "filter": {
                "status": [],
                "idDeclType": [],
                "idCertObjectType": [],
                "idProductType": [],
                "idGroupRU": [],
                "idGroupEEU": [],
                "idTechReg": [],
                "idApplicantType": [],
                "regDate": {"minDate": None, "maxDate": None},
                "endDate": {"minDate": None, "maxDate": None},
                "columnsSearch": [],
                "idProductOrigin": [],
                "idProductEEU": [],
                "idProductRU": [],
                "idDeclScheme": [],
                "awaitOperatorCheck": None,
                "editApp": None,
                "violationSendDate": None,
                "isProtocolInvalid": None,
                "checkerAIResult": None,
                "checkerAIProtocolsResults": None,
                "checkerAIProtocolsMistakes": None,
                "hiddenFromOpen": None,
            },
            "columnsSort": [{"column": "declDate", "sort": "DESC"}],
        }
        data = await self._post_json(DECLARATION_SEARCH_URL, payload, referer=f"{BASE_URL}/rds/declaration")
        items = data.get("items") or []

        results = []
        for item in items:
            item_id = str(item.get("id") or "")
            url = f"{BASE_URL}/rds/declaration/view/{item_id}/common"
            reg_date = item.get("declDate") or ""
            end_date = item.get("declEndDate") or ""
            status_id = str(item.get("idStatus") or "")
            status = STATUS_MAP.get(status_id, f"Неизвестный ({status_id})" if status_id else "")

            results.append(
                LookupResult(
                    input_number="",
                    registry_type="declaration",
                    registry_number=normalize_number(item.get("number")),
                    id=item_id,
                    url=url,
                    reg_date=str(reg_date or ""),
                    end_date=str(end_date or ""),
                    status_id=status_id,
                    status=status,
                )
            )
        return results

    async def _search_certificates(self, number: str) -> list[dict[str, Any]]:
        payload = {
            "size": 10,
            "page": 0,
            "filter": {
                "idCertScheme": [],
                "regDate": {"startDate": None, "endDate": None},
                "endDate": {"startDate": None, "endDate": None},
                "columnsSearch": [{"column": "number", "search": number}],
            },
            "columnsSort": [{"column": "date", "sort": "DESC"}],
        }
        data = await self._post_json(CERTIFICATE_SEARCH_URL, payload, referer=f"{BASE_URL}/rss/certificate")
        return data.get("items") or []

    async def _search_declarations(self, number: str) -> list[dict[str, Any]]:
        payload = {
            "size": 10,
            "page": 0,
            "count": 0,
            "filter": {
                "status": [],
                "idDeclType": [],
                "idCertObjectType": [],
                "idProductType": [],
                "idGroupRU": [],
                "idGroupEEU": [],
                "idTechReg": [],
                "idApplicantType": [],
                "regDate": {"minDate": None, "maxDate": None},
                "endDate": {"minDate": None, "maxDate": None},
                "columnsSearch": [{"name": "number", "search": number, "type": 0}],
                "number": number,
                "idProductOrigin": [],
                "idProductEEU": [],
                "idProductRU": [],
                "idDeclScheme": [],
                "awaitOperatorCheck": None,
                "editApp": None,
                "violationSendDate": None,
                "isProtocolInvalid": None,
                "checkerAIResult": None,
                "checkerAIProtocolsResults": None,
                "checkerAIProtocolsMistakes": None,
                "hiddenFromOpen": None,
            },
            "columnsSort": [{"column": "declDate", "sort": "DESC"}],
        }
        data = await self._post_json(DECLARATION_SEARCH_URL, payload, referer=f"{BASE_URL}/rds/declaration")
        return data.get("items") or []

    async def _post_json(self, url: str, payload: dict[str, Any], referer: str) -> dict[str, Any]:
        refreshed_after_forbidden = False
        last_error: Exception | None = None

        for attempt in range(self._retries):
            token = await self._token_manager.get_token()
            try:
                response = await self._client.post(
                    url,
                    json=payload,
                    headers=self._headers(token, referer),
                )
            except httpx.HTTPError as exc:
                last_error = exc
                if attempt < self._retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise

            if response.status_code in {401, 403} and not refreshed_after_forbidden:
                refreshed_after_forbidden = True
                self._token_manager.clear()
                await self._token_manager.refresh(force=True)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                last_error = httpx.HTTPStatusError(
                    f"HTTP {response.status_code} from {url}",
                    request=response.request,
                    response=response,
                )
                if attempt < self._retries - 1:
                    await asyncio.sleep(2**attempt)
                    continue

            response.raise_for_status()
            return response.json()

        if last_error:
            raise last_error
        raise RuntimeError(f"Request failed: {url}")

    @staticmethod
    def _headers(token: str, referer: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": referer,
            "lkId": "",
            "orgId": "",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        }

    @staticmethod
    def _select_result(number: str, items: list[dict[str, Any]], registry_type: str) -> LookupResult:
        matches = [item for item in items if normalize_number(item.get("number")) == number]

        if not matches:
            return LookupResult(input_number=number, registry_type="not_found")
        if len(matches) > 1:
            return LookupResult(
                input_number=number,
                registry_type="ambiguous",
                error=f"{len(matches)} exact matches in {registry_type} registry",
            )

        item = matches[0]
        item_id = str(item.get("id") or "")
        if registry_type == "certificate":
            url = f"{BASE_URL}/rss/certificate/view/{item_id}/baseInfo"
            reg_date = item.get("date") or ""
            end_date = item.get("endDate") or ""
        else:
            url = f"{BASE_URL}/rds/declaration/view/{item_id}/common"
            reg_date = item.get("declDate") or ""
            end_date = item.get("declEndDate") or ""

        status_id = str(item.get("idStatus") or "")
        status = STATUS_MAP.get(status_id, f"Неизвестный ({status_id})" if status_id else "")

        return LookupResult(
            input_number=number,
            registry_type=registry_type,
            registry_number=normalize_number(item.get("number")),
            id=item_id,
            url=url,
            reg_date=str(reg_date or ""),
            end_date=str(end_date or ""),
            status_id=status_id,
            status=status,
        )
