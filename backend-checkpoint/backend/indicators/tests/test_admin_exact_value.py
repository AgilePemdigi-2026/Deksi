from datetime import date
from decimal import Decimal

from django.contrib import admin
from django.contrib.admin.templatetags.admin_list import result_headers
from django.contrib.admin.utils import lookup_field
from django.test import RequestFactory

from indicators.admin import ObservationAdmin
from indicators.models import Observation
from indicators.tests.support import IndicatorCase


class ExactValueAdminTests(IndicatorCase):
    def setUp(self):
        super().setUp()
        self.reviewer.is_superuser = True
        self.reviewer.save(update_fields=["is_superuser"])
        self.model_admin = ObservationAdmin(Observation, admin.site)
        self.factory = RequestFactory()
        self.observation(value="2")
        self.observation(value="10", observation_date=date(2000, 2, 29))

    def changelist(self, ordering=None):
        request = self.factory.get("/admin/indicators/observation/", {} if ordering is None else {"o": ordering})
        request.user = self.reviewer
        return self.model_admin.get_changelist_instance(request)

    def value_column(self, changelist):
        return next((index, name) for index, name in enumerate(changelist.list_display)
                    if name in {"value", "display_value"})

    def test_exact_value_header_does_not_offer_lexical_number_sort(self):
        changelist = self.changelist()
        index, _ = self.value_column(changelist)
        self.assertFalse(list(result_headers(changelist))[index]["sortable"])

    def test_crafted_admin_sort_parameter_cannot_sort_text_values(self):
        index, _ = self.value_column(self.changelist())
        for ordering in [str(index), f"-{index}"]:
            with self.subTest(ordering=ordering):
                changelist = self.changelist(ordering)
                fields = [str(value).lstrip("-") for value in changelist.queryset.query.order_by]
                self.assertNotIn("value", fields)

    def test_display_preserves_all_decimal_digits_without_float_cast(self):
        row = self.observation(value=Decimal("999999999999999999.999999"), observation_date=date(2000, 3, 31))
        row.refresh_from_db()
        _, name = self.value_column(self.changelist())
        _, _, displayed = lookup_field(name, row, self.model_admin)
        self.assertEqual(str(displayed), "999999999999999999.999999")
