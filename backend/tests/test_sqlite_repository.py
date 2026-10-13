import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.decision_engine.engine import evaluate
from app.persistence.models import CaseRecord
from app.persistence.repository import CaseStorageError
from app.persistence.sqlite_repository import EXCERPT_LENGTH, SqliteCaseRepository
from app.schemas.business_case import (
    BusinessCaseConfirmationRequest,
    ConfirmedBusinessCase,
    PriorityRanking,
)
from tests.helpers import analysis_payload, requirement


def _record(
    case_id: str = "a" * 32,
    created_at: datetime | None = None,
    business_case: str = "Una aplicacion interna con trafico estable y presupuesto limitado.",
) -> CaseRecord:
    payload = analysis_payload(
        business_case,
        available_budget=requirement("low", "detected", ["presupuesto limitado"]),
        demand_pattern=requirement("constant", "detected", ["trafico estable"]),
    )
    request = BusinessCaseConfirmationRequest.model_validate(
        {
            "business_case": payload["business_case"],
            "requirements": payload["requirements"],
            "priority_ranking": {"never_stop_working": 1, "lowest_cost": 2},
        }
    )
    confirmed = ConfirmedBusinessCase(
        business_case=request.business_case,
        requirements=request.requirements,
        additional_context=request.additional_context,
        priority_ranking=request.priority_ranking,
    )
    return CaseRecord(
        id=case_id,
        created_at=created_at or datetime.now(UTC),
        confirmed=confirmed,
        recommendation=evaluate(confirmed.requirements, PriorityRanking()),
    )


def test_saved_case_is_returned_unchanged(tmp_path: Path) -> None:
    repository = SqliteCaseRepository(tmp_path / "cases.sqlite3")
    record = _record()

    repository.save(record)

    assert repository.get(record.id) == record


def test_unknown_id_returns_none(tmp_path: Path) -> None:
    assert SqliteCaseRepository(tmp_path / "cases.sqlite3").get("no-existe") is None


def test_cases_persist_across_repository_instances(tmp_path: Path) -> None:
    path = tmp_path / "cases.sqlite3"
    record = _record()
    SqliteCaseRepository(path).save(record)

    assert SqliteCaseRepository(path).get(record.id) == record


def test_nothing_is_written_to_disk_until_first_use(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "cases.sqlite3"

    SqliteCaseRepository(path)

    assert not path.parent.exists()


def test_parent_directory_is_created_on_first_use(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "cases.sqlite3"

    SqliteCaseRepository(path).list_recent()

    assert path.exists()


def test_duplicate_id_is_rejected(tmp_path: Path) -> None:
    repository = SqliteCaseRepository(tmp_path / "cases.sqlite3")
    repository.save(_record())

    with pytest.raises(CaseStorageError):
        repository.save(_record())


def test_list_recent_orders_newest_first_and_honours_limit(tmp_path: Path) -> None:
    repository = SqliteCaseRepository(tmp_path / "cases.sqlite3")
    now = datetime.now(UTC)
    for index in range(3):
        repository.save(_record(case_id=f"{index:032d}", created_at=now + timedelta(seconds=index)))

    summaries = repository.list_recent(limit=2)

    assert [summary.id for summary in summaries] == [f"{2:032d}", f"{1:032d}"]


def test_summary_truncates_long_business_cases(tmp_path: Path) -> None:
    repository = SqliteCaseRepository(tmp_path / "cases.sqlite3")
    repository.save(_record(business_case="palabra " * 100))

    excerpt = repository.list_recent()[0].business_case_excerpt

    assert len(excerpt) <= EXCERPT_LENGTH
    assert excerpt.endswith("…")


def test_unreadable_stored_case_raises_storage_error(tmp_path: Path) -> None:
    path = tmp_path / "cases.sqlite3"
    repository = SqliteCaseRepository(path)
    repository.save(_record())
    with sqlite3.connect(path) as connection:
        connection.execute("UPDATE cases SET recommendation_json = '{\"obsoleto\": true}'")

    with pytest.raises(CaseStorageError):
        repository.get("a" * 32)


def test_unusable_database_path_raises_storage_error(tmp_path: Path) -> None:
    # Una carpeta no se puede abrir como archivo SQLite.
    with pytest.raises(CaseStorageError):
        SqliteCaseRepository(tmp_path).list_recent()
