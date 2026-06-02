# Bugfix Requirements Document

## Introduction

The `s3-artifacts-bucket-policy.yml` module in the account-wide-infrastructure stack causes a `CREATE_FAILED` state with error "Invalid principal in policy (Service: S3, Status Code: 400)". The bucket policy uses named `Principal` ARNs with wildcard patterns that are backwards from the actual role naming convention, and S3 validates that named principals exist at policy creation time. This prevents the account-wide infrastructure stack from deploying when no matching roles exist yet.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the bucket policy is created with `Principal.AWS` ARNs using the pattern `arn:aws:iam::${AWS::AccountId}:role${RolePath}CodePipelineServiceRole-*` THEN the system fails with "Invalid principal in policy" because the wildcard suffix `CodePipelineServiceRole-*` does not match actual role names where the role type is a suffix (e.g., `acme-Worker-myapp-test-CodePipelineServiceRole`)

1.2 WHEN the bucket policy is created with named `Principal.AWS` ARNs and no IAM roles matching the pattern currently exist in the account THEN the system rejects the policy entirely because S3 bucket policies validate that named principals exist at creation time

1.3 WHEN the bucket policy uses the pattern `arn:aws:iam::${AWS::AccountId}:role${RolePath}CloudFormationSvcRole-*` THEN the system fails because the wildcard placement assumes the role type is a prefix followed by a wildcard, but the actual convention is `*-CloudFormationSvcRole`

### Expected Behavior (Correct)

2.1 WHEN the bucket policy is created THEN the system SHALL use `Principal: "*"` with an `aws:PrincipalArn` `ArnLike` condition to allow wildcard patterns that match roles regardless of whether they currently exist

2.2 WHEN the ArnLike condition patterns are evaluated THEN the system SHALL use the correct pattern `arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodePipelineServiceRole` where the wildcard precedes the role type suffix

2.3 WHEN the ArnLike condition patterns are evaluated THEN the system SHALL use the correct pattern `arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CodeBuildServiceRole` where the wildcard precedes the role type suffix

2.4 WHEN the ArnLike condition patterns are evaluated THEN the system SHALL use the correct pattern `arn:aws:iam::${AWS::AccountId}:role${RolePath}*-CloudFormationSvcRole` where the wildcard precedes the role type suffix

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a request is made without secure transport (aws:SecureTransport = false) THEN the system SHALL CONTINUE TO deny all S3 actions on the bucket and its objects via the DenyNonSecureTransportAccess statement

3.2 WHEN a matching CodePipeline or CodeBuild service role accesses the bucket THEN the system SHALL CONTINUE TO allow s3:GetObject, s3:GetObjectVersion, and s3:GetBucketVersioning on the bucket and its objects (WhitelistedGet)

3.3 WHEN a matching CodePipeline or CodeBuild service role writes to the bucket THEN the system SHALL CONTINUE TO allow s3:PutObject on the bucket and its objects (WhitelistedPut)

3.4 WHEN the bucket policy is applied THEN the system SHALL CONTINUE TO scope access only to the S3ArtifactsBucketRegional resource ARN and its objects

3.5 WHEN the EnableS3ArtifactsBucket condition is false THEN the system SHALL CONTINUE TO not create the bucket policy resource
