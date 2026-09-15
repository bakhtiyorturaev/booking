# Load testing

Load tests must run against a staging deployment with PostgreSQL and Redis, never
against production or the local SQLite database.

```powershell
pip install -r requirements-dev.txt
$env:LOAD_TEST_BRANCH_ID="branch-uuid"
$env:LOAD_TEST_DATE="2026-08-20"
locust -f load_tests/locustfile.py --host https://staging.example.com
```

For booking writes, set `LOAD_TEST_ACCOUNTS_FILE` to a JSON array containing a
different paid test account and future slot for each virtual user:

```json
[
  {
    "access_token": "test-token",
    "zone_id": "zone-uuid",
    "starts_at": "2026-08-20T10:00:00+05:00",
    "ends_at": "2026-08-20T11:00:00+05:00",
    "quantity": 1
  }
]
```

Start with 100 users, then 300, 500 and 1000. A release passes when p95 is under
800 ms for reads, under 1500 ms for booking writes, error rate is below 1%, no
capacity is oversold, and database/worker saturation remains below 80%.
