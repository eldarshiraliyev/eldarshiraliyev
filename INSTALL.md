# Eldar Shiraliyev — Premium Minimalist GitHub Profile

Rich English-language profile README with an acid-lime accent, custom SVG artwork, broad GitHub activity visuals, and GitHub Actions automation for the pinned-project section.

## Files
- `README.md` — profile content and layout.
- `assets/profile-header.svg` — custom banner.
- `assets/profile-footer.svg` — custom footer.
- `.github/workflows/update-profile.yml` — scheduled/manual workflow.
- `scripts/update_pinned_projects.py` — GitHub GraphQL API sync script.

## Install
1. Create a **public** repository named exactly `eldarshiraliyev` if you do not already have it.
2. Copy every file and folder from this ZIP into the repository root, preserving structure.
3. Commit and push.
4. Open the repository's **Actions** tab and enable GitHub Actions if prompted.
5. Open **Update pinned projects in profile README** and choose **Run workflow** for the first sync.
6. Pin/unpin repositories on your profile. The workflow checks every 12 hours; you can also run it manually.

## Permissions
The workflow uses built-in `GITHUB_TOKEN`, not a personal access token. In repository **Settings → Actions → General → Workflow permissions**, enable **Read and write permissions** so the workflow can commit changes. Organization policies can override this setting.

## Notes
- The GraphQL query reads up to six repositories pinned on the public profile.
- Third-party stats/icon services may occasionally rate-limit or fail.
- Review the first generated README after the workflow runs.
- Never add secrets or tokens to the README or commit them to the repository.
