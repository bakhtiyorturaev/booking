# Branch workflow

- `dev`: shared development branch. Developers push their changes here.
- `prod`: release branch. The repository owner reviews and promotes tested changes from `dev` through a pull request.

Use `prod` as the GitHub default branch. The repository uses only `dev` and `prod` for ongoing work.

## Developer workflow

```bash
git fetch origin
git switch dev
git pull --rebase origin dev
# Make and commit changes.
git push origin dev
```

Never force-push shared branches. If a push is rejected, fetch and rebase before retrying.

## Release workflow

1. Test `dev` locally or in staging.
2. Open a pull request with base `prod` and compare `dev`.
3. The repository owner reviews the diff and checks, then merges the pull request.
4. Production deployments must use `prod`. Creating this branch does not change any existing deployment configuration.

## Required GitHub protection

In Settings → Rules → Rulesets, configure a rule targeting `prod`:

- Require a pull request before merging.
- Require code owner review and dismiss stale approvals.
- Block force pushes and deletion.
- Give only `@bakhtiyorturaev` permission to bypass the rule (for reviewing and merging releases authored by the owner).

Keep ordinary developer pushes enabled on `dev`.
The CODEOWNERS file requests the owner's review; enforcement requires the GitHub rule above.
