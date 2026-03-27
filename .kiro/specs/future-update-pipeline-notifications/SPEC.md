# SPEC: Replace EventBridge Notification Rules with CodeStarNotifications

## Status: Future (Pending service role deployment)

## Summary

Replace the current EventBridge Rules + SNS InputTransformer notification approach in all three pipeline templates with `AWS::CodeStarNotifications::NotificationRule`. The current approach sends the entire InputTemplate JSON as the SNS message body, resulting in emails where the `Subject`/`Message` JSON keys appear as raw text rather than being parsed into proper email subject and body fields. CodeStarNotifications natively understands CodePipeline events and produces well-formatted notifications with proper email subjects.

## Prerequisite

The `template-service-role-pipeline.yml` service role must be updated and deployed **before** any pipeline stack updates. Version v0.0.15 adds the required `codestar-notifications:*` and `sns:*` permissions. All users must update their service role stacks first.

## Background

### Current Approach (EventBridge + SNS InputTransformer)

Each pipeline template currently defines:
- 1 `AWS::SNS::Topic` (`PipelineNotificationTopic`) with email subscription
- 3 `AWS::Events::Rule` (Started, Succeeded, Failed) with `InputTransformer` targeting the SNS topic
- 1 `AWS::SNS::TopicPolicy` allowing `events.amazonaws.com` to publish

**Problem:** EventBridge sends the entire `InputTemplate` output as the raw SNS message body. The JSON `{"Subject": "...", "Message": "..."}` structure is not parsed by SNS into separate subject/body fields. Recipients see JSON syntax in their emails.

### Proposed Approach (CodeStarNotifications)

Replace the above with:
- 1 `AWS::SNS::Topic` (retained, with updated policy)
- 1 `AWS::CodeStarNotifications::NotificationRule` targeting the SNS topic
- 1 `AWS::SNS::TopicPolicy` updated to allow `codestar-notifications.amazonaws.com`

**Benefits:**
- Native CodePipeline integration with proper email formatting
- Proper email subject lines (e.g., "SUCCEEDED: Pipeline acme-myapp-prod-Pipeline")
- Richer event coverage (stage-level, action-level events available)
- Fewer resources (1 notification rule replaces 3 EventBridge rules)
- No InputTransformer formatting issues

## Affected Templates

| Template | Current Version | Change Type |
|----------|----------------|-------------|
| `templates/v2/pipeline/template-pipeline.yml` | v2.0.20 | PATCH (non-breaking) |
| `templates/v2/pipeline/template-pipeline-github.yml` | v2.0.3 | PATCH (non-breaking) |
| `templates/v2/pipeline/template-pipeline-build-only.yml` | v2.0.5 | PATCH (non-breaking) |

This is a non-breaking change: notification delivery mechanism changes but no parameters, resource logical IDs used by other stacks, or outputs are affected. The SNS topic logical ID (`PipelineNotificationTopic`) is retained so existing subscriptions are preserved.

## Detailed Changes Per Template

### Resources to Remove

From each pipeline template, remove:
- `PipelineStartedRule` (`AWS::Events::Rule`)
- `PipelineSucceededRule` (`AWS::Events::Rule`)
- `PipelineFailedRule` (`AWS::Events::Rule`)

### Resources to Add

Add to each pipeline template:

```yaml
PipelineNotificationRule:
  Type: AWS::CodeStarNotifications::NotificationRule
  Condition: IsNotDevelopment
  Properties:
    Name: !Sub "${Prefix}-${ProjectId}-${StageId}-Pipeline-Notifications"
    DetailType: BASIC
    Resource: !Sub "arn:aws:codepipeline:${AWS::Region}:${AWS::AccountId}:${Prefix}-${ProjectId}-${StageId}-Pipeline"
    EventTypeIds:
      - codepipeline-pipeline-pipeline-execution-started
      - codepipeline-pipeline-pipeline-execution-succeeded
      - codepipeline-pipeline-pipeline-execution-failed
    Targets:
      - TargetType: SNS
        TargetAddress: !Ref PipelineNotificationTopic
    Tags:
      "atlantis:ApplicationDeploymentId": !Sub "${Prefix}-${ProjectId}-${StageId}"
```

### Resources to Modify

Update `PipelineNotificationTopicPolicy` in each template — change the principal from `events.amazonaws.com` to `codestar-notifications.amazonaws.com`:

```yaml
PipelineNotificationTopicPolicy:
  Type: AWS::SNS::TopicPolicy
  Properties:
    PolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Sid: AllowCodeStarNotificationsToPublish
          Effect: Allow
          Principal:
            Service: codestar-notifications.amazonaws.com
          Action: sns:Publish
          Resource: !Ref PipelineNotificationTopic
    Topics:
      - !Ref PipelineNotificationTopic
```

### Resources to Retain (No Changes)

- `PipelineNotificationTopic` (`AWS::SNS::Topic`) — retained as-is to preserve existing email subscriptions

### Conditions

Add `Condition: IsNotDevelopment` to `PipelineNotificationRule` so it is only created when the pipeline exists (non-DEV environments). The `PipelineNotificationTopic` and `PipelineNotificationTopicPolicy` can remain unconditional (current behavior) or optionally be made conditional — this is a separate decision.

## Event Type IDs Reference

Available CodePipeline event type IDs for `AWS::CodeStarNotifications::NotificationRule`:

### Pipeline Execution (recommended minimum)
- `codepipeline-pipeline-pipeline-execution-started`
- `codepipeline-pipeline-pipeline-execution-succeeded`
- `codepipeline-pipeline-pipeline-execution-failed`
- `codepipeline-pipeline-pipeline-execution-canceled`
- `codepipeline-pipeline-pipeline-execution-resumed`
- `codepipeline-pipeline-pipeline-execution-superseded`

### Stage Execution (optional, for more granular notifications)
- `codepipeline-pipeline-stage-execution-started`
- `codepipeline-pipeline-stage-execution-succeeded`
- `codepipeline-pipeline-stage-execution-failed`
- `codepipeline-pipeline-stage-execution-canceled`
- `codepipeline-pipeline-stage-execution-resumed`

### Action Execution (optional, most granular)
- `codepipeline-pipeline-action-execution-started`
- `codepipeline-pipeline-action-execution-succeeded`
- `codepipeline-pipeline-action-execution-failed`
- `codepipeline-pipeline-action-execution-canceled`

### Manual Approval (optional)
- `codepipeline-pipeline-manual-approval-needed`
- `codepipeline-pipeline-manual-approval-succeeded`
- `codepipeline-pipeline-manual-approval-failed`

The initial implementation should use the three pipeline execution events (started, succeeded, failed) to match current behavior. Additional events can be added later or exposed as a parameter.

## Service Role Dependency

The `template-service-role-pipeline.yml` (v0.0.15) adds these permissions:

```yaml
- Sid: ManageSnsTopicsByResourcePrefix
  Effect: Allow
  Action:
  - sns:CreateTopic
  - sns:DeleteTopic
  - sns:GetTopicAttributes
  - sns:SetTopicAttributes
  - sns:Subscribe
  - sns:Unsubscribe
  - sns:TagResource
  - sns:UntagResource
  - sns:ListSubscriptionsByTopic
  - sns:ListTagsForResource
  Resource:
  - !Sub "arn:aws:sns:${AWS::Region}:${AWS::AccountId}:${Prefix}-*"

- Sid: ManageCodeStarNotificationsByResourcePrefix
  Effect: Allow
  Action:
  - codestar-notifications:CreateNotificationRule
  - codestar-notifications:DeleteNotificationRule
  - codestar-notifications:DescribeNotificationRule
  - codestar-notifications:UpdateNotificationRule
  - codestar-notifications:Subscribe
  - codestar-notifications:Unsubscribe
  - codestar-notifications:TagResource
  - codestar-notifications:UntagResource
  - codestar-notifications:ListTagsForResource
  Resource:
  - !Sub "arn:aws:codestar-notifications:${AWS::Region}:${AWS::AccountId}:notificationrule/*"
```

**Deployment order:**
1. Deploy updated service role stack (v0.0.15) for each prefix
2. Then deploy updated pipeline stacks

## Rollout Plan

1. Deploy `template-service-role-pipeline.yml` v0.0.15 to all environments (adds permissions, no impact on existing stacks)
2. Update pipeline templates (this spec's implementation)
3. Deploy updated pipeline stacks — CloudFormation will:
   - Remove the three EventBridge rules
   - Create the CodeStarNotifications notification rule
   - Update the SNS topic policy principal
   - Retain the SNS topic and existing subscriptions

## Testing

- Verify service role has required permissions before pipeline deployment
- Deploy a test pipeline stack and trigger a pipeline execution
- Confirm email notifications arrive with proper subject lines
- Verify all three states (started, succeeded, failed) produce notifications
- Confirm existing SNS subscriptions continue to receive notifications

## Documentation Updates

After implementation:
- Update `docs/templates/v2/pipeline/template-pipeline-README.md`
- Update `docs/templates/v2/pipeline/template-pipeline-github-README.md`
- Update `docs/templates/v2/pipeline/template-pipeline-build-only-README.md`
- Update `docs/templates/v2/service-role/template-service-role-pipeline-README.md`
- Update `CHANGELOG.md`

## References

- [AWS::CodeStarNotifications::NotificationRule](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-codestarnotifications-notificationrule.html)
- [Events for notification rules on pipelines](https://docs.aws.amazon.com/dtconsole/latest/userguide/concepts.html#events-ref-pipeline)
- [Configure Amazon SNS topics for notifications](https://docs.aws.amazon.com/dtconsole/latest/userguide/set-up-sns.html)
