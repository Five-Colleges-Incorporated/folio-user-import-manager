"""Command for importing user data into FOLIO."""

import typing
from dataclasses import dataclass

import polars as pl
import polars.selectors as cs

from folio_user_import_manager.data import InputData, InputDataOptions
from folio_user_import_manager.folio import Folio, FolioOptions


@dataclass(frozen=True)
class ImportOptions(InputDataOptions, FolioOptions):
    """Options used for importing users into FOLIO."""

    batch_size: int
    max_concurrency: int
    retry_count: int
    failed_user_threshold: float

    deactivate_missing_users: bool
    update_all_fields: bool
    source_type: str | None


@dataclass
class ImportResults:
    """Results of importing users into FOLIO."""


def _clean_nones(obj: dict[str, typing.Any]) -> dict[str, typing.Any]:
    for k in list(obj.keys()):
        if k in ["customFields", "personal"]:
            _clean_nones(obj[k])
        if obj[k] is None:
            del obj[k]

    return obj


def run(options: ImportOptions) -> ImportResults:
    """Import users into FOLIO."""
    with Folio(options).connect() as folio:
        for total, b in InputData(options).batch(options.batch_size):
            batch = b
            cols = batch.collect_schema().names()
            for c in cols:
                if c in ["departments", "preferredEmailCommunication"]:
                    batch = batch.with_columns(pl.col(c).str.split(","))
                if c in ["customFields"]:
                    batch = batch.with_columns(pl.col(c).str.json_decode())
                if c in ["enrollmentDate", "expirationDate", "personal_dateOfBirth"]:
                    batch = batch.with_columns(pl.col(c).dt.to_string())

            cs_personal = cs.starts_with("personal_")

            personal_names = [
                c.replace("personal_", "") for c in cols if c.startswith("personal")
            ]
            if any(personal_names):
                batch = batch.with_columns(
                    pl.struct(cs_personal)
                    .struct.rename_fields(personal_names)
                    .alias("personal"),
                )

            batch = batch.select(cs.all() - cs_personal)
            users = [_clean_nones(u) for u in batch.collect().to_dicts()]
            req = {
                "users": users,
                "totalRecords": total,
                "deactivateMissingUsers": options.deactivate_missing_users,
                "updateOnlyPresentFields": not options.update_all_fields,
            }
            if options.source_type:
                req["sourceType"] = options.source_type

            folio.post_data("/user-import", payload=req)

    return ImportResults()
