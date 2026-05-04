# AI Context

All specs and steering documents for use by AI and Humans are stored in the .kiro directory. Please refer to these documents when interacting with the AI or seeking guidance on project direction.

The AI should always refer to these context files to ensure alignment with project goals, coding standards, and architectural decisions.

### Naming Conventions (Required)

All resource names must follow:

```
Prefix-ProjectId-StageId-Resource
```

S3 buckets have alternatives:

```
Prefix-ProjectId-StageId-AccountId-Region-an (specific deployment instance, no Resource identifier, Regional bucket)
Prefix-ProjectId-AccountId-Region-an (shared instance, no Resource identifier, Regional bucket)
Prefix-ProjectId-StageId-Resource (not preferred)
```

Or, if the organization requires an additional `S3OrgPrefix` identifier:

```
S3BucketNameOrgPrefix-Prefix-ProjectId-StageId-AccountId-Region-an (specific deployment instance, no Resource identifier, Regional bucket)
S3BucketNameOrgPrefix-Prefix-ProjectId-AccountId-Region-an (shared instance, no Resource identifier, Regional bucket)
S3BucketNameOrgPrefix-Prefix-ProjectId-StageId-Resource (not preferred)
```

Where:

* **S3BucketNameOrgPrefix** = organization prefix for all S3 buckets (lowercase)
* **Prefix** = team or org identifier (lowercase)
* **ProjectId** = short identifier for the application (lowercase)
* **StageId** = test, beta/stage, prod (lowercase)
* **Resource** = Purpose of resource: Users, Sessions, Queue, Orders, etc. (Pascal Case, Only first letter of Acronyms are capital)

**AI must respect these naming conventions in all generated example code, IAM roles, and infrastructure.**

These names will be provided to the CloudFormation template as parameters (Prefix, ProjectId, and StageId, S3BucketNameOrgPrefix).

Correct example:

```
Lambda: acme-person-api-test-GetPerson
StepFunction: acme-schedules-prod-Refresh
DynamoDB: acme-schedules-prod-Sessions
DynamoDB: acme-schedules-test-ApiResponseCount
S3: acme-orders-test-123456789012-xy-east-1-an
S3: acorp-acme-orders-123456789012-xy-east-1-an
S3: acorp-acme-orders-logs-123456789012-xy-east-1-an
```

#### S3 

Use S3 Regional bucket name spaces unless otherwise requested.

In some cases, a short Resource name (lower case) may be included after `ProjectId-StageId` if it helps identify the purpose of the bucket beyond the typical project identifier.

However, since bucket names are limited to 63 characters, and `-AccountId-Region-an` takes up about a third of that, and `S3BucketNameOrgPrefix-Prefix-ProjectId-StageId` can also take up a substantial amount, include a `Resource` descriptor only if necessary (e.g. multiple buckets in the same stack, or multiple buckets across shared Project stacks)

### 3.3 IAM Policies – Principle of Least Privilege

AI must follow these rules when generating IAM policies:

* **Never** use AWS managed policies such as `AWSLambdaFullAccess`, `AmazonS3FullAccess`, or `LambdaAll`.
* Always generate **tight, resource-scoped** permissions using ARNs that follow the naming convention.
* Policies must limit both **actions** and **resources**.

Correct:

```yaml
Action:
  - s3:PutObject
Resource:
  - !Sub arn:aws:s3:::${Prefix}-${ProjectId}-${StageId}-output/* 
```

Incorrect:

```yaml
Action: s3:*
Resource: "*"
```