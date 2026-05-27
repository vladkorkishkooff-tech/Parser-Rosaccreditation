from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .client import FsaClient
from .io import read_numbers, write_results
from .models import LookupResult
from .token import TokenManager


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find public Rosakkreditatsiya registry links.")
    parser.add_argument("--input", "-i", default=None, help="Input .csv or .xlsx file. Omit for automatic latest document collection.")
    parser.add_argument("--output", "-o", required=True, help="Output .csv or .xlsx file.")
    parser.add_argument("--limit", "-l", type=int, default=50, help="Number of latest certificates and declarations to fetch when input is omitted. Default: 50.")
    parser.add_argument("--concurrency", "-c", type=int, default=3, help="Concurrent API lookups. Default: 3.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds. Default: 30.")
    parser.add_argument("--token", default=None, help="Optional existing fgis_token. If omitted, Playwright obtains one.")
    args = parser.parse_args(argv)

    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    output_path = Path(args.output)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    token_manager = TokenManager(initial_token=args.token)
    client = FsaClient(token_manager=token_manager, timeout=args.timeout)

    try:
        if args.input:
            input_path = Path(args.input)
            numbers = read_numbers(input_path)
            if not numbers:
                write_results(output_path, [])
                print(f"No numbers found. Empty result written to {output_path}")
                return 0
            print(f"Поиск по входному списку ({len(numbers)} номеров)...")
            results = await _lookup_all(client, numbers, max(1, args.concurrency))
        else:
            print(f"Входной файл не указан. Запускается режим автоматического сбора последних зарегистрированных документов (лимит: по {args.limit} шт.)...")
            print("Запрос сертификатов...")
            certs_task = client.get_latest_certificates(args.limit)
            print("Запрос деклараций...")
            decls_task = client.get_latest_declarations(args.limit)
            results_certs, results_decls = await asyncio.gather(certs_task, decls_task)
            results = results_certs + results_decls
    finally:
        await client.close()

    write_results(output_path, results)
    found = sum(1 for result in results if result.registry_type in {"certificate", "declaration"})
    print(f"Обработано записей: {len(results)}. Найдено документов: {found}. Выходной файл: {output_path}")
    return 0


async def _lookup_all(client: FsaClient, numbers: list[str], concurrency: int) -> list[LookupResult]:
    semaphore = asyncio.Semaphore(concurrency)

    async def lookup_one(number: str) -> LookupResult:
        async with semaphore:
            return await client.lookup(number)

    return list(await asyncio.gather(*(lookup_one(number) for number in numbers)))
