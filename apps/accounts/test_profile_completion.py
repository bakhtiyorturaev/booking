"""`UserProfile.mark_as_completed()` `models.functions.Now()` (DB-side
ifoda) bilan maydonni to'ldirardi — `save()` dan keyin ham instansdagi
`profile_completed_at` haqiqiy `datetime` emas, balki hali bajarilmagan
`Func` obyekti bo'lib qolardi (masalan, keyinroq shu instansni
serializatsiya qilishga urinilsa xatolikka olib kelardi). Endi
`timezone.now()` ishlatiladi."""
import datetime

from django.test import TestCase

from apps.accounts.models import User, UserProfile


class ProfileCompletionTests(TestCase):
    def test_mark_as_completed_sets_a_real_datetime_on_the_instance(self):
        user = User.objects.create_user(username="qa_profile_user", phone="+998901290001")
        profile = UserProfile.objects.create(user=user)

        profile.mark_as_completed()

        self.assertIsInstance(profile.profile_completed_at, datetime.datetime)
        profile.refresh_from_db()
        self.assertIsInstance(profile.profile_completed_at, datetime.datetime)

    def test_mark_as_completed_is_idempotent(self):
        user = User.objects.create_user(username="qa_profile_user2", phone="+998901290002")
        profile = UserProfile.objects.create(user=user)

        profile.mark_as_completed()
        first_value = profile.profile_completed_at
        profile.mark_as_completed()

        self.assertEqual(profile.profile_completed_at, first_value)
