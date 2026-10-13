# Tasks: CodeStar/CodeConnections Pipeline Management Permissions

**Spec:** `0-0-45-codestar-connection-pipeline-permissions`
**Repository version:** v0.0.45 (unreleased)

Implementation checklist. Each task references the requirements it satisfies. Follow module, parameter, comment/metadata, versioning, and documentation steering standards throughout.

- [ ] 1. Version management for `prefix-based-infrastructure.yml`
  - Confirm version handling with the Decision Note in design.md §2: default to bumping PATCH `v2.0.1` → `v2.0.2` with today's date in the `# Version:` header (additive, non-breaking). Do not change MAJOR/MINOR.
  - _Requirements: 2.3, 4.3_

- [ ] 2. Add the conditional connection grant to the deployer role module
  - [ ] 2.1 Edit `templates/v2/modules/management-roles/pipeline-mgmt-role.yml`: add the `Fn::If: [HasGitHubConnection, <PassGitHubConnectionForPipelines statement>, Ref AWS::NoValue]` entry to the inline policy `Statement` list (near the CodePipeline/CodeBuild statements), using long-form intrinsics only. Actions: `PassConnection`, `UseConnection`, `GetConnection`, `GetConnectionToken`, `ListTagsForResource` in both `codestar-connections` and `codeconnections` namespaces; `Resource` = `Fn::ImportValue "${OrgPrefix}-GitHub-Connection-Arn"`; `Condition` = `StringEquals { codestar-connections:PassedToService: codepipeline.amazonaws.com }`. (Exact block in design.md §1.)
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 4.1_
  - [ ] 2.2 Update the module contract comment block: add `HasGitHubConnection` to the required parent conditions; note the `OrgPrefix` export dependency and fail-loudly behavior; note the connection-ARN exception to the `${Prefix}-*` convention.
    - _Requirements: 3.1, 3.2, 4.2_

- [ ] 3. Add the toggle, condition, and metadata group to `prefix-based-infrastructure.yml`
  - [ ] 3.1 Add the `EnableGitHubConnectionAccess` parameter (String, `AllowedValues ["true","false"]`, `Default "false"`, with the ConstraintDescription from design.md §2).
    - _Requirements: 2.1_
  - [ ] 3.2 Add the condition `HasGitHubConnection: !Equals [!Ref EnableGitHubConnectionAccess, "true"]` (gate on the toggle only — do NOT test `OrgPrefix`).
    - _Requirements: 3.1_
  - [ ] 3.3 Add a `"GitHub Connection Access"` group to `AWS::CloudFormation::Interface` ParameterGroups listing `EnableGitHubConnectionAccess`. Confirm existing cfn-lint `ignore_checks` (`E6101`, `W2001`, `W8001`) still cover the new condition (already present; add only if missing).
    - _Requirements: 4.3, 4.6_

- [ ] 4. Verify backward compatibility (default off renders unchanged)
  - Confirm by review that with `EnableGitHubConnectionAccess="false"` the `Fn::If` resolves to `AWS::NoValue` and the rendered deployer-role policy contains no `codestar-connections`/`codeconnections` statements (identical to pre-change). Confirm no existing parameter/output/export/logical ID changed.
  - _Requirements: 2.2, 2.3, 2.4, 2.5_

- [ ] 5. Validate with cfn-lint
  - Run the repository pytest harness (`cfn_linter`) against `templates/v2/account/prefix-based-infrastructure.yml` and confirm it passes. Fix any lint findings. (Modules are validated indirectly through the parent.)
  - _Requirements: 4.6_

- [ ] 6. Update documentation (required — only files affected by this change)
  - [ ] 6.1 `docs/templates/v2/account/prefix-based-infrastructure-README.md`: document `EnableGitHubConnectionAccess` (parameter table + prerequisite/fail-loudly note) and add the new IAM statement to the role's documented permissions. Preserve existing blockquotes.
    - _Requirements: 4.4_
  - [ ] 6.2 `docs/templates/v2/account/account-wide-infrastructure-README.md`: cross-reference that `${OrgPrefix}-GitHub-Connection-Arn` is consumed by the prefix Pipeline Management role when the toggle is on. Preserve existing blockquotes.
    - _Requirements: 4.4_
  - [ ] 6.3 `docs/templates/v2/pipeline/template-pipeline-github-README.md`: clarify deployer-role vs runtime-role connection permissions and the `EnableGitHubConnectionAccess="true"` prerequisite. Preserve existing blockquotes.
    - _Requirements: 4.4_

- [ ] 7. Update `CHANGELOG.md`
  - Add the Added + Fixed entries under `v0.0.45 (unreleased)` (text in design.md §4), referencing this spec and the final `prefix-based-infrastructure.yml` version. Do not modify existing changelog entries.
  - _Requirements: 4.5_

- [ ] 8. Final verification against requirements
  - Re-read requirements.md and confirm each acceptance criterion is satisfied by the implemented changes. Confirm the deprecated `template-service-role-pipeline.yml` and the pipeline template's runtime role were left unchanged (out of scope). Note anything that could not be verified (e.g., live-deploy confirmation of Req 1.5, which requires an AWS account).
  - _Requirements: 1.5, 2.5, out-of-scope confirmations_

## Notes

- Do not add property-based tests (per `testing-guidelines`); cfn-lint + review coverage is sufficient.
- Treat the version Decision Note (design.md §2) as the one maintainer confirmation point; proceed with the PATCH bump default unless told otherwise.
- Live-deploy validation of the `PassConnection` fix (Req 1.5) cannot be performed in this repo without an AWS account; it is verified by construction (correct action + resource + condition) and lint.
