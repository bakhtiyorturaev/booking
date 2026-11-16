"""
Additive QA confirmation tests for blocked-user / revoked-session enforcement.

This file is purely additive -- it does not modify or weaken any existing
test, and it does not change any application logic.

CORRECTED FRAMING (important -- do not read this as "reproducing a bug"):

`User.is_active` (apps/accounts/models.py) is a *live* Python property
computed as `status == Status.ACTIVE`. It is NOT a cached or stored field.
`SessionJWTAuthentication.get_user()` (apps/accounts/authentication.py)
calls `super().get_user(validated_token)` FIRST on every single request,
which does a fresh `User.objects.get(...)` DB query and then checks
`is_active` (rest_framework_simplejwt's `CHECK_USER_IS_ACTIVE` defaults to
True and is not overridden anywhere in config/settings.py's SIMPLE_JWT
block).

The practical consequence: when an admin calls `toggle_status`
(apps/accounts/cabinet_views.py) to BLOCK a user, that takes effect
IMMEDIATELY on that user's very next request -- both for an existing access
token and for a refresh attempt. There is NO caching gap on this path.
`test_blocking_user_immediately_invalidates_their_existing_access_token`
below confirms this is working correctly.

The only cache in this authentication path is `SessionJWTAuthentication`'s
own `SESSION_CACHE_TTL = 60` second cache, which backs a DIFFERENT, narrower
check: `UserSession.revoked_at` / `expires_at`, used by explicit logout and
`revoke_user_session()`. Both call sites for that function already call
`invalidate_session_cache()` synchronously, so that path is also
effectively immediate in practice.
`test_logout_revokes_session_and_invalidates_cache` below is the positive
control proving that path also works. (The only theoretical residual gap is
a request that cached `True` in the ~60s window immediately before a
revoke -- a minor P3 timing note, not a vulnerability; it is not
exercised here because it requires sleeping past a cache TTL in a unit
test, which would be slow and flaky for very little signal.)
"""

from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User, UserSession
from apps.accounts.services.auth_tokens import create_auth_tokens


class BlockedUserSessionEnforcementTests(APITestCase):
    def setUp(self):
        self.target_user = User.objects.create_user(
            username="qa_block_target",
            phone="+998901230101",
            role=User.Role.CUSTOMER,
        )
        self.admin_user = User.objects.create_user(
            username="qa_block_admin",
            phone="+998901230102",
            role=User.Role.ADMIN,
            is_staff=True,
            is_superuser=True,
        )

    def test_blocking_user_immediately_invalidates_their_existing_access_token(self):
        tokens = create_auth_tokens(self.target_user)
        access_token = tokens["access"]

        target_client = APIClient()
        target_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        pre_block_response = target_client.get("/api/v1/bookings/")
        self.assertEqual(
            pre_block_response.status_code,
            200,
            "Sanity check: token should work before the block.",
        )

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)
        toggle_response = admin_client.post(
            f"/api/v1/cabinet/users/{self.target_user.id}/toggle-status/"
        )
        self.assertEqual(toggle_response.status_code, 200, toggle_response.data)

        self.target_user.refresh_from_db()
        self.assertEqual(self.target_user.status, User.Status.BLOCKED)

        # Re-use the SAME, now-stale access token minted before the block.
        post_block_response = target_client.get("/api/v1/bookings/")

        self.assertEqual(
            post_block_response.status_code,
            401,
            "A blocked user's pre-existing access token must be rejected on "
            "its very next request. User.is_active is a live property "
            "re-evaluated from the DB on every request, not a cached/stored "
            "field, so this should never lag behind toggle_status().",
        )

    def test_blocking_user_also_blocks_refresh_token_use(self):
        tokens = create_auth_tokens(self.target_user)

        admin_client = APIClient()
        admin_client.force_authenticate(user=self.admin_user)
        toggle_response = admin_client.post(
            f"/api/v1/cabinet/users/{self.target_user.id}/toggle-status/"
        )
        self.assertEqual(toggle_response.status_code, 200, toggle_response.data)

        refresh_response = APIClient().post(
            "/api/v1/auth/token/refresh/",
            {"refresh": tokens["refresh"]},
            format="json",
        )

        self.assertEqual(
            refresh_response.status_code,
            400,
            "Refreshing a blocked user's token must fail "
            "(refresh_auth_tokens() checks user.is_active and raises "
            "auth.user_inactive).",
        )

    def test_logout_revokes_session_and_invalidates_cache(self):
        """Positive control for the narrower SESSION_CACHE_TTL=60s cache:
        explicit logout (-> revoke_user_session()) must synchronously
        invalidate that cache so the very next request on the same session
        is rejected, not served from a stale cached `True`."""
        tokens = create_auth_tokens(self.target_user)
        access_token = tokens["access"]

        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")

        pre_logout_response = client.get("/api/v1/bookings/")
        self.assertEqual(pre_logout_response.status_code, 200)

        logout_response = client.post("/api/v1/auth/logout/", format="json")
        self.assertEqual(logout_response.status_code, 200, logout_response.data)

        session = UserSession.objects.get(id=tokens["session_id"])
        self.assertIsNotNone(
            session.revoked_at, "Logout must set UserSession.revoked_at."
        )

        post_logout_response = client.get("/api/v1/bookings/")
        self.assertEqual(
            post_logout_response.status_code,
            401,
            "After logout, the same access token's session must be rejected "
            "immediately -- revoke_user_session() calls "
            "invalidate_session_cache() synchronously in the same "
            "transaction as setting revoked_at.",
        )
