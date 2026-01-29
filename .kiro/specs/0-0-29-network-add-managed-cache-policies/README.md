# Initial Specification Prompt

Add option to attach managed cache policies

[Issue #1](https://github.com/63Klabs/atlantis-cfn-template-repo-for-serverless-deployments/issues/1)

The template-network-route53-cloudfront-s3-apigw.yml template should support attaching managed cache policies to the distribution.

Currently two custom cache policies are created:
- CloudFrontCachePolicyStatic
- CloudFrontCachePolicyApi

Instead of creating the latter two, it should be possible to reference managed policies like:
- AWSManagedCachePolicyCachingOptimized
- AWSManagedCachePolicyCachingDisabled
- AWSManagedCachePolicyCachingOptimizedForUncompressedObjects
- AWSManagedCachePolicyElementalMediaPackage

Documentation for each of these polcies should be added. The Parameter description can give a brief explaination:
- CachingOptimized - For most use cases
- CachingDisabled - When you don't want caching
- CachingOptimizedForUncompressedObjects - For uncompressed content
- Elemental-MediaPackage - For media content

An appropriate section for comments linking to AWS documentation should be provided in the resource section when the template is determinging which policy to apply. This will ensure the comments are included in the template's generated README. If not, then we will need to devise a way (perhaps with > just like in readmes) to ensure AI applies comments and highlights the appropriate section in the accompanying template documentation readme file.

For example: 

```yaml
Resources:
  MyResource:
    Type: AWS::CloudFront::Distribution
    Properties:
      # > This is an important comment that should also be in the documentation
      SomeSetting: !Ref SomeParameter
```

The existing distribution and policies.

```yaml
  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Condition: CreateDistribution
    Properties:
      DistributionConfig:
        Comment: !Sub "${Prefix}-${ProjectId}-${StageId}"

        DefaultCacheBehavior:
          CachePolicyId: !If [ StaticOriginIsRoot, !Ref CloudFrontCachePolicyStatic, !Ref CloudFrontCachePolicyApi ]
          TargetOriginId: !If [ StaticOriginIsRoot, "StaticS3Origin", "ApiGatewayOrigin" ]
          ViewerProtocolPolicy: redirect-to-https
          Compress: true
          AllowedMethods: !If
          - StaticOriginIsRoot
          - [HEAD, GET, OPTIONS]
          - [GET, HEAD, OPTIONS, PUT, PATCH, POST, DELETE]
          CachedMethods: [HEAD, GET, OPTIONS]

        CacheBehaviors:
          - !If 
            - HasRouteForStaticOrigin
            - PathPattern: !Sub "/${PathStatic}/*"
              AllowedMethods:
              - GET
              - HEAD
              - OPTIONS
              CachePolicyId: !Ref CloudFrontCachePolicyStatic
              TargetOriginId: StaticS3Origin
              ViewerProtocolPolicy: redirect-to-https
              Compress: true
            - Ref: AWS::NoValue
          - !If 
            - HasRouteForApiInCloudFront
            - PathPattern: !Sub "/${PathApi}/*"
              AllowedMethods: [GET, HEAD, OPTIONS, PUT, PATCH, POST, DELETE]
              CachePolicyId: !Ref CloudFrontCachePolicyApi
              TargetOriginId: ApiGatewayOrigin
              ViewerProtocolPolicy: redirect-to-https
              Compress: true
            - Ref: AWS::NoValue

  CloudFrontCachePolicyStatic:
    Type: AWS::CloudFront::CachePolicy
    Condition: HasStaticOrigin
    Properties:
      CachePolicyConfig:
        Name: !Sub "${Prefix}-${ProjectId}-${StageId}-Static-CachePolicy"
        Comment: S3 Origin
        DefaultTTL: !If [ IsProduction, 86400, 3 ]
        MaxTTL: !If [ IsProduction, 31536000, 10 ]
        MinTTL: 0
        ParametersInCacheKeyAndForwardedToOrigin:
          CookiesConfig:
            CookieBehavior: none
          EnableAcceptEncodingBrotli: false
          EnableAcceptEncodingGzip: false
          QueryStringsConfig:
            QueryStringBehavior: none
          HeadersConfig:
            HeaderBehavior: none

  CloudFrontCachePolicyApi:
    Type: AWS::CloudFront::CachePolicy
    # Condition: ApiIsBehindCloudFront
    Properties:
      CachePolicyConfig:
        Name: !Sub "${Prefix}-${ProjectId}-${StageId}-Api-CachePolicy"
        Comment: Api Origin
        DefaultTTL: 10
        MaxTTL: 30
        MinTTL: 0
        ParametersInCacheKeyAndForwardedToOrigin:
          CookiesConfig:
            CookieBehavior: all
          EnableAcceptEncodingBrotli: false
          EnableAcceptEncodingGzip: false
          QueryStringsConfig:
            QueryStringBehavior: all
          HeadersConfig: !If 
            - HasHeadersToForwardToApi
            - HeaderBehavior: whitelist
              Headers: !Ref HeadersToForwardToApi
            - HeaderBehavior: none

```

We will need to add parameters to configure what policy should be used. 

API and Static will need their own parameters.
- CloudFrontStaticCachePolicy
- CloudFrontStaticCustomCachePolicyArn
- CloudFrontApiCachePolicy
- CloudFrontApiCustomCachePolicyArn

We would like to use few parameters, but may need a secondary parameter if using a custom policy.

Default for static is AWSManagedCachePolicyCachingOptimized
Default for api is AWSManagedCachePolicyCachingDisabled

The 4 AWS provided options should be available for both static and api origins as enum. 2 additional options are "CustomDefault" and "CustomArn"

If "CustomDefault" is selected, then the existing custom policies should be used.
If "CustomArn" is selected, then a CustomCachePolicyArn parameter should be made available.

Conditionals should be created and used in the template.

Currently the CloudFrontCachePolicyApi has no condition, this should be updated to use the new conditional.

Please ask any clarifying questions.