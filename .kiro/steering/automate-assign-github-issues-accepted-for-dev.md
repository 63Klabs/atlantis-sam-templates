---
inclusion: manual
description: "Checks the current GitHub repository for unassigned issues that have the label \"approved for development\", assigns them to the currently logged-in GitHub user, pulls issue details (labels like bug/enhancement, title, body), and creates a new Kiro spec directory with requirements.md containing the issue metadata and a link back to the issue. The repository is detected automatically from the git remote, so this hook is portable across projects. Requires gh cli and the gh auth user to be logged in and have access to the repository."
---

Determine the current GitHub repository by running `gh repo view --json nameWithOwner --jq '.nameWithOwner'`. Use that value (referred to below as REPO) for all subsequent commands so this hook works in any repository without hard-coded values.

Check REPO for unassigned issues with the label `approved for development` using the GitHub CLI (`gh issue list --repo REPO --label 'approved for development' --json number,title,assignees`). For each unassigned, approved for development issue found:

1. Assign the issue to the currently logged-in GitHub user (`gh api user --jq '.login'` to get the username, then `gh issue edit <number> --repo REPO --add-assignee <username>`).

2. Get the issue details including title, body, labels, and number using `gh issue view <number> --repo REPO --json number,title,body,labels,url`.

3. Follow the spec naming convention steering doc to determine the version.

4. Create a new spec directory at `.kiro/specs/{version}-{feature-name}/` where feature-name is derived from the issue title in kebab-case.

5. Create a `requirements.md` file in that spec directory with the following structure:

```markdown
# {Issue Title}

## Metadata

- **GitHub Issue**: [#{number}]({url})
- **Type**: {labels - e.g., bug, enhancement, documentation, etc.}
- **Assigned**: {username}
- **Created from issue**: {date}

## Description

{Issue body content}

## Requirements

- [ ] FR1: {Derive initial requirement from issue description}
```

If there are no unassigned, approved for development issues, report that there are no unassigned issues to process.

List all issues found and specs created when done.
