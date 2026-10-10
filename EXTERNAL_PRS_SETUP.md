# External PR report setup

[EXTERNAL_PRS.md](EXTERNAL_PRS.md) lists public PRs authored by `DisabledAbel` where the repository owner's login differs from `DisabledAbel`. Organization repositories count as external, including organizations you belong to. Private repositories are excluded because this is a public profile.

The updater paginates the user's full PR history, so it includes all dates and avoids GitHub Search's 1,000-result limit. Each run refreshes titles and statuses as well as adding new PRs. API failures preserve the previous report, and unchanged data produces no commit.

## Enable the workflow

1. Put `.github/workflows/update-external-prs.yml`, `scripts/update_external_prs.py`, and `EXTERNAL_PRS.md` on this repository's default branch.
2. In [repository Actions secrets](https://github.com/DisabledAbel/DisabledAbel/settings/secrets/actions), add a repository secret named **`PR_REPORT_PAT`** containing your GitHub personal access token. The token is used only for reading public PR history. A classic PAT can read public data without the `repo` scope; a fine-grained PAT needs access to the public data queried by GitHub GraphQL. It does not need write access to this profile repository.
3. Open **Actions → Update external pull request report → Run workflow** to verify the first refresh.

The schedule runs at **00:37 and 12:37 UTC every day** (every 12 hours). GitHub may delay scheduled runs. Scheduled workflows require the file on the default branch; GitHub may disable schedules in public repositories after 60 days without repository activity.

The workflow's built-in `GITHUB_TOKEN` commits the report with `contents: write`. Repository or organization policy must allow that write, and the default branch must allow bot pushes. Renew the PAT secret before the token expires.

## Run locally

Export `GH_TOKEN` securely in your shell, then run:

```bash
PROFILE_USERNAME=DisabledAbel python3 scripts/update_external_prs.py
```

The script requires only Python 3 and the standard library. Keep the PAT in a secret or local environment variable, never in a tracked file.
