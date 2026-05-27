from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from .client import FsaClient
from .io import read_numbers, write_results
from .models import LookupResult
from .token import TokenManager


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find public Rosakkreditatsiya registry links by document numbers.")
    parser.add_argument("--input", "-i", required=True, help="Input .csv or .xlsx file. Uses 'number' column or first column.")
    parser.add_argument("--output", "-o", required=True, help="Output .csv or .xlsx file.")
    parser.add_argument("--concurrency", "-c", type=int, default=3, help="Concurrent API lookups. Default: 3.")
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP request timeout in seconds. Default: 30.")
    parser.add_argument("--token", default=None, help="Optional existing fgis_token. If omitted, Playwright obtains one.")
    args = parser.parse_args(argv)

    return asyncio.run(_run(args))


async def _run(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)
    if not output_path.suffix:
        output_path = output_path.with_suffix(".xlsx")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    numbers = read_numbers(input_path)

    if not numbers:
        write_results(output_path, [])
        print(f"No numbers found. Empty result written to {output_path}")
        return 0

    token_manager = TokenManager(initial_token=args.token)
    client = FsaClient(token_manager=token_manager, timeout=args.timeout)

    try:
        results = await _lookup_all(client, numbers, max(1, args.concurrency))
    finally:
        await client.close()

    write_results(output_path, results)
    found = sum(1 for result in results if result.registry_type in {"certificate", "declaration"})
    print(f"Processed: {len(results)}. Found: {found}. Output: {output_path}")
    return 0


async def _lookup_all(client: FsaClient, numbers: list[str], concurrency: int) -> list[LookupResult]:
    semaphore = asyncio.Semaphore(concurrency)

    async def lookup_one(number: str) -> LookupResult:
        async with semaphore:
            return await client.lookup(number)

    return list(await asyncio.gather(*(lookup_one(number) for number in numbers)))
