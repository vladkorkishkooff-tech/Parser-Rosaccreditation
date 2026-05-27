from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class LookupResult:
    input_number: str
    registry_type: str
    registry_number: str = ""
    id: str = ""
    url: str = ""
    reg_date: str = ""
    end_date: str = ""
    status_id: str = ""
    status: str = ""
    error: str = ""

    def to_row(self) -> dict[str, str]:
        return asdict(self)
