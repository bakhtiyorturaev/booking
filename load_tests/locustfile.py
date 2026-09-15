import json
import os
from itertools import cycle
from pathlib import Path

from locust import HttpUser, between, task


BRANCH_ID = os.getenv("LOAD_TEST_BRANCH_ID", "")
TEST_DATE = os.getenv("LOAD_TEST_DATE", "")
accounts_path = os.getenv("LOAD_TEST_ACCOUNTS_FILE", "")
accounts = json.loads(Path(accounts_path).read_text()) if accounts_path else []
account_pool = cycle(accounts) if accounts else None


class CatalogUser(HttpUser):
    weight = 8
    wait_time = between(1, 3)

    @task(3)
    def branches(self):
        self.client.get("/api/v1/branches/?page_size=20", name="branches")

    @task(1)
    def availability(self):
        if BRANCH_ID and TEST_DATE:
            self.client.get(
                f"/api/v1/branches/{BRANCH_ID}/availability/",
                params={"date": TEST_DATE, "duration_minutes": 60},
                name="availability",
            )


class BookingUser(HttpUser):
    weight = 2
    wait_time = between(2, 5)

    def on_start(self):
        self.account = next(account_pool) if account_pool else None
        if self.account:
            self.client.headers["Authorization"] = f"Bearer {self.account['access_token']}"

    @task
    def create_booking_once(self):
        if not self.account or self.account.get("completed"):
            return
        hold_response = self.client.post(
            "/api/v1/booking-holds/",
            json={
                "zone_id": self.account["zone_id"],
                "starts_at": self.account["starts_at"],
                "ends_at": self.account["ends_at"],
                "quantity": self.account.get("quantity", 1),
            },
            name="booking hold",
        )
        if hold_response.status_code == 201:
            self.client.post(
                "/api/v1/bookings/",
                json={"hold_id": hold_response.json()["id"]},
                name="booking create",
            )
        self.account["completed"] = True
