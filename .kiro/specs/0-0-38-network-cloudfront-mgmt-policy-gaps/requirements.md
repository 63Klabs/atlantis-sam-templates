# Requirements Document

## Introduction

This spec addresses multiple permissions gaps in `network-cloudfront-mgmt-policy.yml` that cause deployment failures for the `template-network-route53-cloudfront-s3-apigw.yml` template. The gaps include missing CloudFront Origin Request Policy read permissions, missing API Gateway `/apis` resource access for ApiMapping validation, and an S3 log bucket ARN pattern that does not match actual bucket names.

- **GitHub Issue**: [#8](https://github.com/63Klabs/atlantis-sam-templates/issues/8)
- **Type**: bug
- **Assigned**: chadkluck
- **Created from issue**: 2026-06-12

## Glossary

- **Origin Request Policy**: A CloudFront policy that controls which headers, cookies, and query strings are included in requests forwarded to the origin.
- **ApiMapping**: An `AWS::ApiGatewayV2::ApiMapping` resource that maps an API stage to a custom domain name.
- **UseS3BucketNameOrgPrefix**: A CloudFormation condition that, when true, prepends an organization-specific prefix (`S3BucketNameOrgPrefix`) to S3 bucket name patterns.
- **Management Role Policy**: An IAM policy attached to a CloudFormation service role that grants permissions needed to deploy and manage resources within a specific prefix scope.

## Description

The `network-cloudfront-mgmt-policy.yml` has several permissions gaps that will cause deployment failures for the `template-network-route53-cloudfront-s3-apigw.yml` template.

### Affected Templates

- `templates/v2/modules/management-roles/network-cloudfront-mgmt-policy.yml` (the service role policy)
- Deployments of `templates/v2/network/template-network-route53-cloudfront-s3-apigw.yml`

### Gap 1: Missing CloudFront Origin Request Policy permissions

The network template uses a managed Origin Request Policy (`AllViewerExceptHostHeader`) in `OriginRequestPolicyId`. CloudFormation needs to read/validate this policy during distribution creation and updates, but the current service role policy only has Cache Policy and OAC permissions.

### Gap 2: Missing API Gateway /apis resource for ApiMapping

The template creates `AWS::ApiGatewayV2::ApiMapping` which requires CloudFormation to call `GET /apis/{apiId}` to validate the API reference. The current policy covers `/domainnames` and `/domainnames/*` but not `/apis` or `/apis/*`.

### Gap 3: S3BucketReadForLogging pattern mismatch

The `S3BucketReadForLogging` statement uses a pattern that resolves to `acme-123456789012-us-east-1-*` but the actual log bucket name includes ProjectId (e.g. `acme-myproj-access-logs-123456789012-us-east-1-an`), so the role cannot read the log bucket.

## Requirements

### 1. CloudFront Origin Request Policy

1.1 A `CloudFrontOriginRequestPolicyRead` statement SHALL be added granting `cloudfront:GetOriginRequestPolicy`, `cloudfront:GetOriginRequestPolicyConfig`, and `cloudfront:ListOriginRequestPolicies` on resource `"*"`

### 2. API Gateway /apis Access

2.1 An `ApiGatewayV2ReadApis` statement SHALL be added granting `apigateway:GET` on `arn:aws:apigateway:${Region}::/apis` and `arn:aws:apigateway:${Region}::/apis/*`

### 3. S3 Log Bucket Pattern Fix

3.1 The `S3BucketReadForLogging` resource pattern SHALL be updated to match all buckets under the prefix, using `Fn::If` with `UseS3BucketNameOrgPrefix` to produce `${S3BucketNameOrgPrefix}-${Prefix}-*` when the org prefix is enabled, or `${Prefix}-*` when it is not. Example pattern:
```yaml
Resource:
  - Fn::Sub:
    - "arn:aws:s3:::${BucketPrefix}-*"
    - BucketPrefix:
        Fn::If:
          - UseS3BucketNameOrgPrefix
          - Fn::Sub: "${S3BucketNameOrgPrefix}-${Prefix}"
          - Fn::Sub: "${Prefix}"
```

### 4. Validation

4.1 The modified template SHALL pass cfn-lint validation with no errors

4.2 Unit tests SHALL verify the new statements and corrected S3 pattern exist with correct actions and resources
