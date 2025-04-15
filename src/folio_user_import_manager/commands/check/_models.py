"""Models for check command."""

from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

import pandera.polars as pla
import polars as pl

from folio_user_import_manager.folio import FolioOptions


@dataclass(frozen=True)
class CheckOptions(FolioOptions):
    """Options used for checking an import's viability."""

    data_location: Path | dict[str, Path]


@dataclass
class CheckResults:
    """Results of checking an import's viablity."""

    @property
    def folio_ok(self) -> bool:
        """Is the connection to FOLIO ok?"""
        return self.folio_error is None

    """The error (if there is one) connecting to FOLIO during the check."""
    folio_error: str | None = None

    @property
    def schema_ok(self) -> bool:
        """Is the data valid?"""
        return self.schema_errors is None

    """The errors (if there are any) with the validity of the data."""
    schema_errors: dict[str, pla.errors.SchemaErrors] | None = None

    @property
    def read_ok(self) -> bool:
        """Can we read the data as a csv?"""
        return self.read_errors is None

    """The errors (if there are any) encountered reading the data."""
    read_errors: dict[str, pl.exceptions.PolarsError] | None = None

    def write_results(self, stream: TextIO) -> None:
        """Pretty prints the results of the check."""
        report = []
        if self.folio_ok:
            report.append("✅ FOLIO connection is good!")
        else:
            report.append(f"❌ FOLIO connection: {self.folio_error}")

        if self.read_ok and self.schema_ok:
            report.append("✅ Data is good!")
        else:
            report.append("❌ Data has issues:")
            if self.read_errors:
                for k, v in self.read_errors.items():
                    report.append(f"\t{k}: {v}")
            if self.schema_errors:
                for k, v in self.schema_errors.items():
                    report.append(f"\t{k}: {v}")

        stream.writelines("\n".join(report) + "\n")
