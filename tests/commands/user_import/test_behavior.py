import typing
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from unittest import mock

import httpx
import polars as pl
from pytest_cases import parametrize, parametrize_with_cases


@dataclass
class RetryCase:
    data_location: Path
    retry_count: int
    side_effect: list[Exception]
    call_count: int
    created_records: int
    failed_records: int

    @contextmanager
    def setup(self) -> typing.Any:
        pl.DataFrame({"row": list(range(100))}).write_csv(self.data_location)
        yield


class RetryCases:
    @parametrize(retry_count=[1, 2, 3])
    def case_retry_ok(self, retry_count: int, tmpdir: str) -> RetryCase:
        data = Path(tmpdir) / "data.csv"
        return RetryCase(
            data,
            retry_count,
            [httpx.HTTPError("") for _ in range(retry_count)],
            retry_count + 1,
            100,
            0,
        )

    def case_retry_not_ok(self, tmpdir: str) -> RetryCase:
        data = Path(tmpdir) / "data.csv"
        retry_count = 2
        return RetryCase(
            data,
            retry_count,
            [httpx.HTTPError("") for _ in range(retry_count + 1)],
            retry_count + 1,
            0,
            100,
        )


@mock.patch("pyfolioclient.FolioBaseClient")
@parametrize_with_cases("tc", RetryCases)
def test_retry(base_client_mock: mock.Mock, tc: RetryCase) -> None:
    import folio_user_import_manager.commands.user_import as uut

    # I couldn't figure this out better
    post_data_mock: mock.MagicMock = (
        base_client_mock.return_value.__enter__.return_value.post_data
    )
    post_data_mock.side_effect = [*tc.side_effect, mock.DEFAULT]
    post_data_mock.return_value = {
        "createdRecords": tc.created_records,
        "failedRecords": tc.failed_records,
    }

    with tc.setup():
        res = uut.run(
            uut.ImportOptions(
                "",
                "",
                "",
                "",
                tc.data_location,
                tc.created_records + tc.failed_records + 1,
                1,
                tc.retry_count,
                100.0,
                deactivate_missing_users=False,
                update_all_fields=False,
                source_type=None,
            ),
        )

    assert post_data_mock.call_count == tc.call_count
    assert res.created_records == tc.created_records
    assert res.failed_records == tc.failed_records
