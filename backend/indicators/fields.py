"""Exact observation decimals on SQLite, whose NUMERIC affinity otherwise uses floats.

The application calculates/compares values in Decimal, never SQL arithmetic. Existing
SQLite values already rounded before this migration cannot be reconstructed.
"""
from decimal import Decimal, localcontext

from django.db import models


class ObservationDecimalField(models.DecimalField):
    def get_internal_type(self):
        return "DecimalField"

    def db_type(self, connection):
        if connection.vendor == "sqlite":
            return "text"
        return super().db_type(connection)

    def get_db_prep_value(self, value, connection, prepared=False):
        value = self.to_python(value)
        if value is None:
            return None
        self.run_validators(value)
        with localcontext() as context:
            context.prec = self.max_digits + self.decimal_places + 2
            canonical = value.quantize(Decimal(1).scaleb(-self.decimal_places))
        return format(canonical, "f") if connection.vendor == "sqlite" else canonical

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)
