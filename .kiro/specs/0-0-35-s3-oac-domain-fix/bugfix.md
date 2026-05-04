# Bugfix Requirements Document

## Introduction

On May 1, 2026, some CloudFront distributions fronting S3 buckets using Origin Access Control (OAC) began redirecting browsers to the S3 bucket domain with a 307 status code instead of serving content through CloudFront. The root cause is that CloudFormation's `!GetAtt <BucketLogicalId>.DomainName` returns the old global S3 domain format (`<bucketname>.s3.amazonaws.com`) rather than the regional format (`<bucketname>.s3.<region>.amazonaws.com`) that AWS now requires. The `OriginBucketDomainForCloudFront` output in `template-storage-s3-oac-for-cloudfront.yml` uses this intrinsic function, producing an incorrect domain that causes the redirect. This addresses [#3](https://github.com/63Klabs/atlantis-sam-templates/issues/3).

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the `OriginBucketDomainForCloudFront` output is consumed by a CloudFront distribution's S3 origin configuration THEN the system produces a 307 redirect from the CloudFront domain to the S3 bucket domain (`<bucketname>.s3.amazonaws.com/<path>`) instead of serving the requested content

1.2 WHEN CloudFormation evaluates `!GetAtt OriginBucketRegional.DomainName` THEN the system returns the old global S3 domain format (`<bucketname>.s3.amazonaws.com`) instead of the regional domain format (`<bucketname>.s3.<region>.amazonaws.com`)

### Expected Behavior (Correct)

2.1 WHEN the `OriginBucketDomainForCloudFront` output is consumed by a CloudFront distribution's S3 origin configuration THEN the system SHALL serve the requested content through CloudFront without any redirect

2.2 WHEN the template generates the `OriginBucketDomainForCloudFront` output value THEN the system SHALL produce the regional S3 domain format `https://<bucketname>.s3.<region>.amazonaws.com` using `!Sub` with the bucket reference and `AWS::Region` pseudo-parameter instead of relying on `!GetAtt DomainName`

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the template creates the S3 bucket (`OriginBucketRegional`) THEN the system SHALL CONTINUE TO create the bucket with the same naming convention, encryption, public access block, and logging configuration

3.2 WHEN the template creates the S3 bucket policy (`BucketPolicy`) THEN the system SHALL CONTINUE TO grant CloudFront read-only access and CodeBuild read/write/delete access with the same conditions

3.3 WHEN the `BucketName` output is referenced THEN the system SHALL CONTINUE TO return the bucket name via `!Ref OriginBucketRegional`

3.4 WHEN the `AllowedCloudFrontAndCodeBuild` output is referenced THEN the system SHALL CONTINUE TO return the `${Prefix}-${ProjectId}` value

3.5 WHEN the `InvalidatorArn` condition is true THEN the system SHALL CONTINUE TO create the Lambda permission and S3 event notification configuration unchanged
