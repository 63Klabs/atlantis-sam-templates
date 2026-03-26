# Implementation Plan: Pipeline Notification Formatting

## Overview

Update the `InputTemplate` in all 9 EventBridge rule targets (3 rules × 3 templates) to switch from YAML `|` to `>-`, format messages with labeled fields on separate lines, add "ALERT:" prefix to failure subjects, and include a call-to-action only for failures. This is a non-breaking change (PATCH increment) applied identically across all three pipeline templates.

## Tasks

- [x] 1. Version management
  - [x] 1.1 Increment version for template-pipeline.yml
    - Current version: v2.0.19/2026-03-26
    - Increment PATCH to v2.0.20 and update date to today
    - _Requirements: Version control steering (PATCH > 0, non-breaking change)_
  - [x] 1.2 Increment version for template-pipeline-github.yml
    - Current version: v2.0.2/2026-03-26
    - Increment PATCH to v2.0.3 and update date to today
    - _Requirements: Version control steering (PATCH > 0, non-breaking change)_
  - [x] 1.3 Increment version for template-pipeline-build-only.yml
    - Current version: v2.0.4/2026-03-26
    - Increment PATCH to v2.0.5 and update date to today
    - _Requirements: Version control steering (PATCH > 0, non-breaking change)_

- [x] 2. Update InputTemplate in template-pipeline.yml (CodeCommit)
  - [x] 2.1 Update PipelineStartedRule InputTemplate
    - Switch from `|` to `>-` block scalar
    - Format Message with labeled fields: "Pipeline Execution - STARTED\n\nStatus: STARTED\nPipeline: ...\nExecution ID: ...\nTime: ...\n\nConsole Link: ..."
    - Subject: "Pipeline <pipeline> Started"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 5.3_
  - [x] 2.2 Update PipelineSucceededRule InputTemplate
    - Switch from `|` to `>-` block scalar
    - Format Message with labeled fields, same structure as Started
    - Subject: "Pipeline <pipeline> Succeeded"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.2, 5.3_
  - [x] 2.3 Update PipelineFailedRule InputTemplate
    - Switch from `|` to `>-` block scalar
    - Format Message with labeled fields plus call-to-action: "Please check the pipeline for errors."
    - Subject: "ALERT: Pipeline <pipeline> Failed"
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3, 3.1, 5.3_

- [x] 3. Update InputTemplate in template-pipeline-github.yml (GitHub)
  - [x] 3.1 Update PipelineStartedRule InputTemplate
    - Apply identical InputTemplate as task 2.1
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 4.1, 5.3_
  - [x] 3.2 Update PipelineSucceededRule InputTemplate
    - Apply identical InputTemplate as task 2.2
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.2, 4.1, 5.3_
  - [x] 3.3 Update PipelineFailedRule InputTemplate
    - Apply identical InputTemplate as task 2.3
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3, 3.1, 4.1, 5.3_

- [x] 4. Update InputTemplate in template-pipeline-build-only.yml (CodeCommit build-only)
  - [x] 4.1 Update PipelineStartedRule InputTemplate
    - Apply identical InputTemplate as task 2.1
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 4.1, 5.3_
  - [x] 4.2 Update PipelineSucceededRule InputTemplate
    - Apply identical InputTemplate as task 2.2
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.2, 4.1, 5.3_
  - [x] 4.3 Update PipelineFailedRule InputTemplate
    - Apply identical InputTemplate as task 2.3
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.3, 3.1, 4.1, 5.3_

- [x] 5. Checkpoint - Verify template changes
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Write unit tests for notification formatting
  - [x] 6.1 Create tests/test_pipeline_notifications_unit.py with unit tests
    - Load all three pipeline YAML templates and extract InputTemplate from each EventBridge rule
    - Test JSON structure: each InputTemplate renders to valid JSON with exactly `Subject` and `Message` keys (Property 5)
    - Test subject format per state: Started/Succeeded contain pipeline name and state word; Failed starts with "ALERT:" (Property 2)
    - Test message body labels: each message contains "Status:", "Pipeline:", "Execution ID:", "Time:", "Console Link:" on separate lines (Property 1)
    - Test blank line separation: messages contain `\n\n` for visual section separation (Property 1)
    - Test call-to-action for FAILED only: FAILED message contains "Please check the pipeline for errors."; STARTED and SUCCEEDED do not (Property 3)
    - Test no JSON artifacts in rendered message/subject values: no `{`, `}`, `"Message":`, `"Subject":` in the values (Property 4)
    - Test template parity: compare InputTemplate structures across all three template files for each rule type (Property 6)
    - Test YAML block scalar uses `>-` (not `|`) to ensure no trailing newline
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 3.2, 4.1, 5.1, 5.2, 5.3_

- [ ] 7. Write property-based tests for notification formatting
  - [ ]* 7.1 Write property test for labeled fields and section separation
    - **Property 1: Message body contains labeled fields on separate lines with section separation**
    - Generate random pipeline names, execution IDs, and timestamps using hypothesis strategies
    - Substitute into the message template pattern and verify all labels appear on separate lines with blank-line separation
    - **Validates: Requirements 1.1, 1.2, 1.3**
  - [ ]* 7.2 Write property test for subject line format
    - **Property 2: Subject line contains pipeline name and state-appropriate text with ALERT prefix only for failures**
    - Generate random pipeline names; for each state verify subject contains pipeline name and correct state word, with ALERT: prefix only for FAILED
    - **Validates: Requirements 2.1, 2.2, 2.3**
  - [ ]* 7.3 Write property test for plain text without artifacts
    - **Property 4: Rendered subject and message are plain text without JSON or HTML artifacts**
    - Generate random pipeline names and field values; verify rendered subject and message contain no JSON structural characters or HTML tags
    - **Validates: Requirements 1.4, 5.1, 5.2**

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Update documentation and changelog
  - [x] 9.1 Update documentation for template-pipeline.yml
    - Update `docs/templates/v2/pipeline/template-pipeline-README.md` to reflect notification formatting changes and new version
    - _Requirements: Documentation steering_
  - [x] 9.2 Update documentation for template-pipeline-github.yml
    - Update `docs/templates/v2/pipeline/template-pipeline-github-README.md` to reflect notification formatting changes and new version
    - _Requirements: Documentation steering_
  - [x] 9.3 Update documentation for template-pipeline-build-only.yml
    - Update `docs/templates/v2/pipeline/template-pipeline-build-only-README.md` to reflect notification formatting changes and new version
    - _Requirements: Documentation steering_
  - [x] 9.4 Update CHANGELOG.md
    - Add entries for all three templates documenting the notification formatting improvement under "Fixed" or "Changed"
    - _Requirements: Changelog steering_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using hypothesis
- Unit tests validate specific examples and edge cases
- All three templates must receive identical InputTemplate changes to maintain parity (Requirement 4.1)
