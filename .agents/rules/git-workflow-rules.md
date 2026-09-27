---
trigger: always_on
description: Git workflow and commit rules for the SkillsRepo repository.
---

# Git Workflow & Security Rules

1. **Commit Message Standards**:
   - Write clear, imperative commit messages summarizing structural changes (e.g. `Add FastMCP server`, `Update mcp_config.json`).

2. **Secret Hygiene**:
   - Verify `.gitignore` excludes `.env`, `.venv/`, `__pycache__/`, and `.pytest_cache/` before staging files.
   - Never stage or commit files containing raw personal access tokens or secret keys.

3. **Remote Push Verification**:
   - Verify working tree is clean (`git status`) before and after pushing commits to GitHub.
