# API Ingress Standard

How to put an API Gateway behind the CloudFront distribution created by the [network template](../templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md), identify the client, and make sure requests reach your application only through that distribution.

- [Recommended pattern](#recommended-pattern)
- [Client IP behavior](#client-ip-behavior)
- [Origin secret](#origin-secret)
- [Rotating the secret](#rotating-the-secret)
- [Who can read the secret](#who-can-read-the-secret)
- [Distribution-wide 403 and 404 rewrite](#distribution-wide-403-and-404-rewrite)
- [Optional enforcement with a web ACL](#optional-enforcement-with-a-web-acl)
- [Deployment order](#deployment-order)

## Recommended pattern

Use a **Regional** API Gateway behind the distribution. A Regional API receives the true viewer address and CloudFront's own viewer headers (see [Client IP behavior](#client-ip-behavior)). An edge-optimized API puts a second, AWS-managed CloudFront distribution between your distribution and the API, so the viewer address is lost.

An API Gateway default endpoint (`https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`) stays reachable by anyone who knows the API ID. The distribution cannot disable it, because the distribution's origin is that endpoint. The [origin secret](#origin-secret) lets your application tell requests that came through the distribution from requests that did not.

> **Note:** The origin secret proves that a request passed through a distribution configured with that secret. It does not authenticate the caller. Keep your normal API authorization in place.

## Client IP behavior

Results from runtime checks on 2026-11-08 using mock REST APIs behind a CloudFront distribution that uses the template's managed origin request policy (`Managed-AllViewerExceptHostHeader`).

| API type behind the distribution | `requestContext.identity.sourceIp` | `CloudFront-Viewer-Address` | `X-Forwarded-For` |
|----------------------------------|------------------------------------|-----------------------------|-------------------|
| Regional (REST, verified) | True viewer address | Present, true address. A viewer cannot override it. | A viewer-sent value is kept as the left entries |
| Edge-optimized (REST, verified) | An edge address | Dropped | `viewer, edge, edge` |
| HTTP API, IPv6 viewers | Not tested | Not tested | Not tested |

What this means for your application:

- On a Regional REST API, use `requestContext.identity.sourceIp` or `CloudFront-Viewer-Address` (format `address:port`). A viewer-sent `CloudFront-Viewer-Address`, `CloudFront-Viewer-Country`, or `CloudFront-Viewer-ASN` arrives with CloudFront's value, not the viewer's.
- On an edge-optimized API, neither is usable as a client address. Fall back to `X-Forwarded-For`.
- A viewer-sent `X-Forwarded-For` is passed through to the origin. **Parse it right to left** and stop at the first entry you did not expect to be added by AWS. Never trust the leftmost entry. On an edge-optimized API the form is `viewer, edge, edge`, so the viewer address is third from the right.
- HTTP APIs and IPv6 viewers were not tested. Verify them in your own environment before depending on the result.

## Origin secret

When `ApiOriginProtection` is `"true"`, CloudFront adds the header `X-Atlantis-Origin-Secret` to every request it sends to the API Gateway origin. A viewer cannot supply its own value: CloudFront overwrites a viewer-sent header of the same name (verified for both Regional and edge-optimized APIs).

The value is read from the Secrets Manager secret named:

```
Prefix-ProjectId-StageId-OriginSecret
```

For example, `acme-orders-prod-OriginSecret`. The secret must exist in the same region as the network stack before the stack is created or updated with `ApiOriginProtection="true"`. The application stack creates it.

### Create the secret in the application stack

Generate the value with `GenerateSecretString` so no person ever sees or stores it.

```yaml
Parameters:
  Prefix:
    Type: String
  ProjectId:
    Type: String
  StageId:
    Type: String

Resources:
  OriginSecret:
    Type: AWS::SecretsManager::Secret
    Properties:
      Name: !Sub "${Prefix}-${ProjectId}-${StageId}-OriginSecret"
      Description: Shared secret CloudFront sends in X-Atlantis-Origin-Secret
      GenerateSecretString:
        PasswordLength: 48
        ExcludePunctuation: true

  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      Environment:
        Variables:
          ORIGIN_SECRET_ID: !Ref OriginSecret   # the secret ARN; read the value at runtime
      Policies:
        - Statement:
            - Effect: Allow
              Action: secretsmanager:GetSecretValue
              Resource: !Ref OriginSecret
```

Read the value from Secrets Manager at runtime, and cache it for a short time so a rotation takes effect without a redeploy. Do not copy the value into an environment variable or a parameter.

> **Note:** The pipeline's CloudFormation service role can create, update, and delete secrets named `Prefix-ProjectId-StageId-*`. It cannot read secret values. If creating the secret fails with `AccessDenied`, update the pipeline stack so the role picks up the Secrets Manager statement.

### What the application must do

1. **Compare in constant time.** Use `crypto.timingSafeEqual` (Node.js), `hmac.compare_digest` (Python), or the equivalent. Do not use `==`.
2. **Never log the header** or the secret, including in error messages and request dumps.
3. **Reject when the secret is missing.** If the application has no configured secret, or the secret is empty, or the header is absent, reject the request. Do not fall back to allowing it.
4. **Use a status other than 403 or 404 on mismatch.** Return 401 or 421, for example. See [Distribution-wide 403 and 404 rewrite](#distribution-wide-403-and-404-rewrite).
5. **Count rejections** so a misconfiguration or probing shows up in your metrics.

## Rotating the secret

Updating the secret does not change the distribution, so CloudFormation does not read the new value on its own. Changing `ApiOriginSecretRevision` modifies the distribution (the revision is appended to its comment), which makes CloudFormation read the secret again. Secrets Manager automatic rotation does not apply the new value to the distribution by itself.

1. Change the application to accept both the old and the new value, and deploy it.
2. Put the new value in the secret.
3. Update the network stack with a changed `ApiOriginSecretRevision` (for example `r1`, then `r2`). Allowed characters are letters, numbers, dots, and dashes, up to 32 characters.
4. Wait until the distribution status is `Deployed`, plus a margin. Propagation to edge locations varies. In one measurement a new value reached the edge about a minute after the update began and CloudFormation finished at about two minutes.
5. Remove the old value from the application.

If you roll back a failed update, the distribution resolves whatever the secret holds at that time. CloudFormation does not remember which secret version an earlier deployment used.

## Who can read the secret

The value is stored in the CloudFront distribution configuration. Any principal with `cloudfront:GetDistribution` or `cloudfront:GetDistributionConfig` can read it, and these actions are included in most administrator and read-only roles. The value does not appear in CloudFormation outputs, events, resource details, or the processed template (verified).

Treat the secret as an ingress token, not as a credential for sensitive actions.

If you encrypt the secret with a customer-managed KMS key, every principal that reads the value needs `kms:Decrypt` on that key. This includes the application role. The default `aws/secretsmanager` key needs no extra permission. The CloudFormation service role used by the network stack reads the secret during stack operations, so on a customer-managed key it needs `kms:Decrypt` as well.

## Distribution-wide 403 and 404 rewrite

When the network stack has a static origin, the distribution has `CustomErrorResponses` that map 403 and 404 responses to `/index.html` with status 200. CloudFront cannot scope this to one behavior, so it also applies to **API responses**.

If your application answers a missing or wrong secret with 403 or 404, the viewer sees a 200 page instead of an error. Use another status for a secret mismatch (401 or 421), and avoid returning 403 or 404 from the API where the viewer must see the real status.

## Optional enforcement with a web ACL

The application check runs after API Gateway has accepted the request. To reject earlier, attach an AWS WAF web ACL to the API stage with a rule that blocks requests whose `X-Atlantis-Origin-Secret` header does not match the secret value.

- The web ACL belongs to the API's stack, not the network template.
- It adds WAF charges (web ACL, rule, and per-request).
- The rule needs the secret value, so the value is stored in the web ACL as well. Rotate it with the same sequence: the web ACL must accept both values until the distribution has the new one.

## Deployment order

1. Redeploy the network service role so it can read the secret. Use `prefix-based-infrastructure.yml`, `template-service-role-network-cloudfront.yml`, or `template-service-role-network-full.yml`, whichever you use.
2. Update the pipeline stack of the application so its CloudFormation role can create the secret.
3. Deploy the application stack, which creates `Prefix-ProjectId-StageId-OriginSecret`.
4. Update the network stack with `ApiOriginProtection="true"`. The stack fails with an assertion message if no API Gateway sits behind CloudFront (`ApiGatewayId` set and `DomainForApiGateway` empty are required).
5. Enable enforcement in the application. Confirm that a direct call to the `execute-api` endpoint is rejected and that a call through the distribution succeeds.

Do not enable enforcement before step 4 finishes and the distribution is `Deployed`, or the application will reject legitimate traffic.

## Related documentation

- [Network template: template-network-route53-cloudfront-s3-apigw](../templates/v2/network/template-network-route53-cloudfront-s3-apigw-README.md)
- [End-User Documentation](./README.md)
