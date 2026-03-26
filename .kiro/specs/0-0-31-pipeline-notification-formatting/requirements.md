# Requirements Document

## Introduction

The pipeline templates (`template-pipeline.yml`, `template-pipeline-github.yml`, and `template-pipeline-build-only.yml`) send email notifications via SNS when pipeline executions start, succeed, or fail. Currently, the EventBridge InputTransformer produces a raw JSON-like message body with escaped newline characters (`\n`), resulting in emails that are difficult to read. This feature improves the notification formatting so that emails are human-friendly with clear structure, labeled fields, and visual separation between sections.

## Glossary

- **Pipeline_Template**: The CloudFormation template that defines the CodePipeline, EventBridge rules, and SNS notification resources. There are three variants: `template-pipeline.yml` (CodeCommit), `template-pipeline-github.yml` (GitHub), and `template-pipeline-build-only.yml` (CodeCommit, build-only without CloudFormation deploy stage).
- **Notification_Message**: The email body content delivered to subscribers of the pipeline SNS topic when a pipeline execution state change occurs.
- **Notification_Subject**: The email subject line delivered to subscribers of the pipeline SNS topic.
- **InputTransformer**: The EventBridge target configuration that maps event fields and formats them into the SNS message payload.
- **Pipeline_Event**: An EventBridge event emitted by CodePipeline when execution state changes to STARTED, SUCCEEDED, or FAILED.
- **Console_Link**: A URL that navigates directly to the pipeline view in the AWS CodePipeline console.

## Requirements

### Requirement 1: Human-Readable Email Body Structure

**User Story:** As a DevOps engineer, I want pipeline notification emails to have a clearly structured body with labeled fields on separate lines, so that I can quickly scan the email and understand the pipeline status.

#### Acceptance Criteria

1. WHEN a Pipeline_Event occurs, THE InputTransformer SHALL produce a Notification_Message with each field (status, pipeline name, execution ID, timestamp, console link) on a separate line.
2. WHEN a Pipeline_Event occurs, THE InputTransformer SHALL produce a Notification_Message that uses plain-text labels before each value (e.g., "Status:", "Pipeline:", "Execution ID:", "Time:", "Console Link:").
3. WHEN a Pipeline_Event occurs, THE InputTransformer SHALL produce a Notification_Message that includes a blank line between the header summary and the detail fields for visual separation.
4. THE Notification_Message SHALL use plain text formatting compatible with email clients that do not support HTML rendering.

### Requirement 2: Descriptive Email Subject Lines

**User Story:** As a DevOps engineer, I want pipeline notification email subjects to clearly indicate the status and identify the pipeline, so that I can triage notifications from my inbox without opening them.

#### Acceptance Criteria

1. WHEN a Pipeline_Event with state STARTED occurs, THE InputTransformer SHALL produce a Notification_Subject that contains the pipeline name and the word "Started".
2. WHEN a Pipeline_Event with state SUCCEEDED occurs, THE InputTransformer SHALL produce a Notification_Subject that contains the pipeline name and the word "Succeeded".
3. WHEN a Pipeline_Event with state FAILED occurs, THE InputTransformer SHALL produce a Notification_Subject that contains the pipeline name, the word "Failed", and a leading "ALERT:" prefix to indicate urgency.

### Requirement 3: Status-Specific Message Content

**User Story:** As a DevOps engineer, I want failure notifications to include an actionable prompt directing me to investigate, so that I can respond to failures faster.

#### Acceptance Criteria

1. WHEN a Pipeline_Event with state FAILED occurs, THE Notification_Message SHALL include a call-to-action line prompting the recipient to check the pipeline for errors.
2. WHEN a Pipeline_Event with state STARTED or SUCCEEDED occurs, THE Notification_Message SHALL include the Console_Link as a reference without an error-specific call-to-action.

### Requirement 4: Consistent Formatting Across All Pipeline Templates

**User Story:** As a DevOps engineer, I want the notification format to be identical in all three pipeline templates (CodeCommit, GitHub, and build-only), so that I receive a consistent experience regardless of the source repository type or pipeline configuration.

#### Acceptance Criteria

1. THE Pipeline_Template for CodeCommit (`template-pipeline.yml`) SHALL use the same Notification_Message structure and Notification_Subject format as the Pipeline_Template for GitHub (`template-pipeline-github.yml`) and the Pipeline_Template for build-only (`template-pipeline-build-only.yml`).
2. WHEN a change is made to the notification format in one Pipeline_Template, THE other Pipeline_Templates SHALL receive the same change to maintain parity.

### Requirement 5: Removal of Raw JSON Wrapper from Message Body

**User Story:** As a DevOps engineer, I want the email body to contain only the formatted message text without JSON syntax artifacts, so that the notification reads as a natural email.

#### Acceptance Criteria

1. THE Notification_Message SHALL NOT be wrapped in JSON curly braces or include JSON key-value syntax (e.g., `"Message":`) in the delivered email body.
2. THE Notification_Subject SHALL NOT be wrapped in JSON curly braces or include JSON key-value syntax (e.g., `"Subject":`) in the delivered email subject line.
3. WHEN EventBridge delivers the event to the SNS topic, THE InputTransformer SHALL format the payload so that SNS interprets the subject and message as separate fields rather than a single JSON blob.
