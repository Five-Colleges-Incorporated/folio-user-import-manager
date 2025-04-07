from pathlib import Path

import pandera.polars as pla
import polars as pl

from ._models import CheckOptions

# https://dev.folio.org/guides/uuids/
_FOLIO_UUID = r""
r"^[a-fA-F0-9]{8}-"
r"[a-fA-F0-9]{4}-"
r"[1-5][a-fA-F0-9]{3}-"
r"[89abAB][a-fA-F0-9]{3}-"
r"[a-fA-F0-9]{12}$"


def run(
    options: CheckOptions,
) -> tuple[
    dict[str, pla.errors.SchemaErrors] | None,
    dict[str, pl.exceptions.PolarsError] | None,
]:
    schema_errors: dict[str, pla.errors.SchemaErrors] = {}
    read_errors: dict[str, pl.exceptions.PolarsError] = {}
    user_data_import_schema = pla.DataFrameSchema(
        {
            "username": pla.Column(
                str,
                description="A unique name belonging to a user. "
                "Typically used for login",
                unique=True,
            ),
            "externalSystemId": pla.Column(
                str,
                description="A unique ID that corresponds to an external authority",
                unique=True,
            ),
            "id": pla.Column(
                str,
                description="A globally unique (UUID) identifier for the user",
                unique=True,
                required=False,
                nullable=True,
                checks=[pla.Check.str_matches(_FOLIO_UUID)],
            ),
        },
        strict=False,
    )

    for n, p in (
        {"data": options.data_location}
        if isinstance(options.data_location, Path)
        else options.data_location
    ).items():
        try:
            pl.read_csv(p)
        except pl.exceptions.PolarsError as e:
            read_errors[n] = e

        data: pl.DataFrame | None
        try:
            data = pl.read_csv(p, ignore_errors=True)
        except pl.exceptions.PolarsError as e:
            if n not in read_errors:
                read_errors[n] = e
            continue

        try:
            user_data_import_schema.validate(data, lazy=True)
        except pla.errors.SchemaError as se:
            schema_errors[n] = pla.errors.SchemaErrors(
                user_data_import_schema,
                [se],
                data,
            )
        except pla.errors.SchemaErrors as se:
            schema_errors[n] = se

    return (
        schema_errors if len(schema_errors) > 0 else None,
        read_errors if len(read_errors) > 0 else None,
    )
