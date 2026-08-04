# Modules/Nested Stacks

Store nested stacks for use in your templates.

## Account-Wide Modules

Located in `templates/v2/modules/account-wide/`:

- **s3-artifacts-bucket.yml** - S3 bucket for build artifacts with lifecycle policies

## Pipeline Modules

Located in `templates/v2/modules/pipeline/`:

Pipeline modules provide reusable CloudFormation resources for CI/CD pipeline templates via AWS::Include. These modules enable consistent pipeline infrastructure across CodeCommit and GitHub-based deployments.

### Notification Resources (5 modules)

Used by all pipeline templates (template-pipeline.yml, template-pipeline-github.yml, template-pipeline-build-only.yml):

- **pipeline-notification-topic.yml** - SNS topic for pipeline event notifications with email subscription
- **pipeline-notification-started-rule.yml** - EventBridge rule that sends notification when pipeline execution starts
- **pipeline-notification-succeeded-rule.yml** - EventBridge rule that sends notification when pipeline execution succeeds
- **pipeline-notification-failed-rule.yml** - EventBridge rule that sends notification when pipeline execution fails
- **pipeline-notification-topic-policy.yml** - SNS topic policy allowing EventBridge to publish notifications

### Source and Build Resources (5 modules)

Core pipeline resources:

- **source-event-service-role.yml** - IAM role for EventBridge to trigger pipeline execution (used by all three templates)
- **source-event-rule.yml** - EventBridge rule to detect CodeCommit repository changes (used by template-pipeline.yml and template-pipeline-build-only.yml only; GitHub template uses CodeConnections webhook)
- **codebuild-log-group.yml** - CloudWatch log group for CodeBuild project logs (used by all three templates)
- **codebuild-service-role.yml** - IAM service role for CodeBuild with S3, SSM, and logging permissions (used by all three templates)
- **codebuild-project.yml** - CodeBuild project with Amazon Linux 2023 container image (used by all three templates)

### Deployment Resources (2 modules)

Used only by full pipeline templates (template-pipeline.yml and template-pipeline-github.yml):

- **cloudformation-svc-role.yml** - IAM service role for CloudFormation to create application infrastructure
- **codedeploy-service-role.yml** - IAM service role for CodeDeploy Lambda deployments

### PostDeploy Resources (3 modules)

Optional resources for post-deployment integration tests and validation (used by template-pipeline.yml and template-pipeline-github.yml when PostDeployStageEnabled=true):

- **postdeploy-service-role.yml** - IAM service role for PostDeploy CodeBuild project
- **postdeploy-project.yml** - CodeBuild project for post-deployment tasks
- **postdeploy-log-group.yml** - CloudWatch log group for PostDeploy project logs

### Module Consumption by Template

| Template | Modules Consumed | Count |
|----------|------------------|-------|
| template-pipeline.yml | All 15 modules | 15 |
| template-pipeline-github.yml | All except source-event-rule.yml | 14 |
| template-pipeline-build-only.yml | Notification (5) + Source/Build (5) only | 10 |

### Using Pipeline Modules

Pipeline modules are referenced via AWS::Include transforms in the parent templates. Each template requires two additional parameters:

- **S3ModuleLocation** - S3 bucket name where modules are stored
- **S3ModuleNamespace** - Namespace prefix for module paths (default: "atlantis")

Modules are resolved from: `s3://${S3ModuleLocation}/${S3ModuleNamespace}/templates/v2/modules/pipeline/<module-name>.yml`