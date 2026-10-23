"""`ServiceType.save()` har bir chaqiruvda butun jadvalni
(`select_for_update()`, WHERE shartisiz) qulflardi — nom yoki
`sort_order`/`is_active` kabi oddiy maydonni o'zgartirish ham daraxt
tuzilishiga (`parent`) umuman aloqasi yo'q bo'lsa-da, boshqa barcha xizmat
turlarini saqlashni navbatga qo'yardi. Endi to'liq jadval qulfi faqat
`parent` haqiqatan o'zgarganda olinadi."""
from unittest.mock import patch

from django.db.models.query import QuerySet
from django.test import TestCase

from apps.core.models import ServiceType


class ServiceTypeSaveLockingTests(TestCase):
    def setUp(self):
        self.root = ServiceType.objects.create(code="qa-root", name="QA Root")
        self.other = ServiceType.objects.create(code="qa-other", name="QA Other")

    def test_plain_field_update_does_not_lock_whole_table(self):
        self.root.name = "QA Root Renamed"
        with patch.object(QuerySet, "select_for_update", wraps=QuerySet.select_for_update, autospec=True) as locked:
            self.root.save()
        locked.assert_not_called()

    def test_parent_change_still_locks_whole_table(self):
        with patch.object(QuerySet, "select_for_update", wraps=QuerySet.select_for_update, autospec=True) as locked:
            self.other.parent = self.root
            self.other.save()
        locked.assert_called_once()

    def test_cycle_detection_still_works_after_fix(self):
        self.other.parent = self.root
        self.other.save()
        self.root.parent = self.other
        with self.assertRaises(Exception):
            self.root.save()
