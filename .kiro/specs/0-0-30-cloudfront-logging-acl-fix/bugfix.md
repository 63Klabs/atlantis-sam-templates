# Bugfix Requirements Document

## Introduction

The S3 access logs bucket template (`templates/v2/storage/template-storage-s3-access-logs.yml`) is intended to serve as a logging destination for both S3 server access logs and CloudFront standard (legacy) access logs. However, when the bucket is used as a CloudFront logging destination, deployment fails with the error: "The S3 bucket that you specified for CloudFront logs does not enable ACL access."

CloudFront standard logging requires ACL-based write access to the destination bucket. The current template unconditionally blocks all ACL access (`BlockPublicAcls: true`) and provides no mechanism to opt in to the ACL grants, ownership controls, and bucket policy statements required by CloudFront legacy logging.

The fix introduces a new `AllowLegacyCloudFrontLogs` parameter (defaulting to `false`) that lets users opt in to CloudFront legacy logging support. When enabled, the template conditionally relaxes `BlockPublicAcls`, sets `ObjectOwnership: BucketOwnerPreferred`, and adds a CloudFront log delivery bucket policy statement. When disabled (the default), the bucket retains its current secure configuration, ensuring existing deployments are unaffected.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the bucket created by this template is specified as the logging destination for a CloudFront distribution THEN the deployment fails with the error "The S3 bucket that you specified for CloudFront logs does not enable ACL access" because there is no way to enable ACL grants

1.2 WHEN the bucket is created THEN the system unconditionally sets `BlockPublicAcls: true` with no parameter or condition to allow ACL grants required by CloudFront standard logging

1.3 WHEN the bucket is created THEN the system does not configure `OwnershipControls` with `ObjectOwnership: BucketOwnerPreferred`, which is required for CloudFront to use ACL-based log delivery

1.4 WHEN the bucket is created THEN the bucket policy does not include a statement allowing the CloudFront log delivery service (`delivery.logs.amazonaws.com`) to write log objects

### Expected Behavior (Correct)

2.1 WHEN the template is deployed THEN the system SHALL provide an `AllowLegacyCloudFrontLogs` parameter with allowed values `true` and `false`, defaulting to `false`

2.2 WHEN `AllowLegacyCloudFrontLogs` is set to `true` THEN the system SHALL set `BlockPublicAcls: false` to allow ACL grants required by CloudFront standard logging, while keeping other public access blocks enabled (`BlockPublicPolicy: true`, `IgnorePublicAcls: true`, `RestrictPublicBuckets: true`)

2.3 WHEN `AllowLegacyCloudFrontLogs` is set to `true` THEN the system SHALL configure `OwnershipControls` with `ObjectOwnership: BucketOwnerPreferred` to allow CloudFront ACL-based log delivery while ensuring the bucket owner retains ownership of all objects

2.4 WHEN `AllowLegacyCloudFrontLogs` is set to `true` THEN the bucket policy SHALL include a statement allowing the CloudFront log delivery service (`delivery.logs.amazonaws.com`) to perform `s3:PutObject` on the bucket, with `s3:x-amz-acl` condition set to `bucket-owner-full-control`

2.5 WHEN `AllowLegacyCloudFrontLogs` is set to `false` (the default) THEN the system SHALL set `BlockPublicAcls: true` and SHALL NOT add ownership controls or the CloudFront log delivery policy statement, preserving the current secure configuration

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the bucket is used as a destination for S3 server access logs THEN the system SHALL CONTINUE TO accept logs from the S3 logging service (`logging.s3.amazonaws.com`) via the existing bucket policy statement

3.2 WHEN non-secure transport is used to access the bucket THEN the system SHALL CONTINUE TO deny access via the `DenyNonSecureTransportAccess` policy statement

3.3 WHEN the bucket is created THEN the system SHALL CONTINUE TO apply server-side encryption with AES256 (SSE-S3)

3.4 WHEN the bucket is created THEN the system SHALL CONTINUE TO apply the lifecycle rule that deletes logs after the configured `LogExpirationInDays`

3.5 WHEN the bucket is created THEN the system SHALL CONTINUE TO set `BlockPublicPolicy: true`, `IgnorePublicAcls: true`, and `RestrictPublicBuckets: true` to prevent public access

3.6 WHEN the stack is deleted or the bucket resource is replaced THEN the system SHALL CONTINUE TO retain the bucket (DeletionPolicy: Retain, UpdateReplacePolicy: Retain)

3.7 WHEN the bucket is created THEN the system SHALL CONTINUE TO generate the bucket name using the same naming convention based on Prefix, ProjectId, Region, AccountId, and optional S3BucketNameOrgPrefix

3.8 WHEN `AllowLegacyCloudFrontLogs` is not specified THEN the system SHALL default to `false` so that existing deployments are not affected by the new parameter
