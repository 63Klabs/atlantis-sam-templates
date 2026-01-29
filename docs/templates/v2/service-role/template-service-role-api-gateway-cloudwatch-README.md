# template-service-role-api-gateway-cloudwatch.yml

Account-level IAM role for API Gateway to write logs to CloudWatch.

**Version:** Not versioned (account-level configuration)  
**Last Updated:** N/A  
**Template:** [templates/v2/service-role/template-service-role-api-gateway-cloudwatch.yml](../../../../templates/v2/service-role/template-service-role-api-gateway-cloudwatch.yml)

## Overview

This template creates an account-level IAM role that allows API Gateway to write logs to CloudWatch Logs. This is a one-time setup required per AWS account per region to enable CloudWatch logging for API Gateway REST APIs.

### Key Features

- **Account-Level Configuration**: One-time setup per AWS account per region
- **Automatic Configuration**: Automatically configures API Gateway account settings
- **AWS Managed Policy**: Uses AWS-managed policy for CloudWatch Logs access
- **No Parameters**: Simple deployment with no configuration required
- **Minimal Resources**: Creates only the necessary IAM role and account configuration

### Use Cases

- Enable CloudWatch logging for API Gateway REST APIs
- Centralized logging configuration at the account level
- Required for API Gateway execution logs and access logs
- Prerequisite for monitoring and debugging API Gateway APIs

### Prerequisites

- AWS account with permissions to create IAM roles
- Permissions to configure API Gateway account settings
- No other prerequisites

> **Important:** This template should be deployed once per AWS account per region. Multiple deployments in the same account/region will conflict.

## Parameters

This template has no parameters. It creates a standard configuration that works for all API Gateway APIs in the account.

## Resources

This template creates the following resources:

- [ApiGatewayCloudWatchLogsRole](#apigatewaycloudwatchlogsrole) - AWS::IAM::Role
- [ApiGatewayAccount](#apigatewayaccount) - AWS::ApiGateway::Account

### ApiGatewayCloudWatchLogsRole

Type: AWS::IAM::Role

IAM role that API Gateway assumes to write logs to CloudWatch.

**Key Properties:**
- **Trust Policy**: Allows apigateway.amazonaws.com to assume the role
- **Managed Policy**: AmazonAPIGatewayPushToCloudWatchLogs (AWS-managed)
- **Permissions**: Create log groups, create log streams, put log events

**Managed Policy Permissions:**
The AWS-managed policy `AmazonAPIGatewayPushToCloudWatchLogs` provides:
- `logs:CreateLogGroup`
- `logs:CreateLogStream`
- `logs:DescribeLogGroups`
- `logs:DescribeLogStreams`
- `logs:PutLogEvents`
- `logs:GetLogEvents`
- `logs:FilterLogEvents`

### ApiGatewayAccount

Type: AWS::ApiGateway::Account

Configures the API Gateway account to use the CloudWatch Logs role.

**Key Properties:**
- **CloudWatchRoleArn**: References the ApiGatewayCloudWatchLogsRole
- **Account-Level**: Applies to all API Gateway APIs in the account/region
- **Automatic**: No manual configuration required after deployment

> **Note:** This resource configures the account-level setting for API Gateway. Once set, all API Gateway APIs in the account can use CloudWatch logging.

## Outputs

### ApiGatewayCloudWatchLogsRoleArn

ARN of the API Gateway CloudWatch Logs role.

**Value:** ARN of ApiGatewayCloudWatchLogsRole

**Usage:** Reference this ARN if you need to verify the role configuration or troubleshoot logging issues.

**Example Value:** `arn:aws:iam::123456789012:role/ApiGatewayCloudWatchLogsRole`

## Examples

### Basic Deployment

```bash
# Deploy using AWS CLI
aws cloudformation create-stack \
  --stack-name api-gateway-cloudwatch-role \
  --template-body file://template-service-role-api-gateway-cloudwatch.yml \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Deployment using SAM CLI

```bash
# Deploy using SAM CLI
sam deploy \
  --template-file template-service-role-api-gateway-cloudwatch.yml \
  --stack-name api-gateway-cloudwatch-role \
  --capabilities CAPABILITY_IAM \
  --region us-east-1
```

### Verify Deployment

After deployment, verify the configuration:

```bash
# Check API Gateway account settings
aws apigateway get-account --region us-east-1

# Expected output includes:
# "cloudwatchRoleArn": "arn:aws:iam::123456789012:role/ApiGatewayCloudWatchLogsRole"
```

## Enabling Logging in API Gateway

After deploying this template, you can enable logging for your API Gateway APIs:

### For REST APIs

1. **Navigate to API Gateway Console**
2. **Select your API**
3. **Go to Stages**
4. **Select a stage**
5. **Enable CloudWatch Logs**:
   - Logs tab → Enable CloudWatch Logs
   - Select log level (ERROR, INFO, or OFF)
   - Enable Execution Logging and/or Access Logging

### Using CloudFormation

```yaml
Resources:
  ApiGatewayStage:
    Type: AWS::ApiGateway::Stage
    Properties:
      RestApiId: !Ref MyRestApi
      StageName: prod
      MethodSettings:
        - ResourcePath: "/*"
          HttpMethod: "*"
          LoggingLevel: INFO
          DataTraceEnabled: true
          MetricsEnabled: true
```

### Using SAM

```yaml
Resources:
  MyApi:
    Type: AWS::Serverless::Api
    Properties:
      StageName: prod
      AccessLogSetting:
        DestinationArn: !GetAtt ApiAccessLogGroup.Arn
        Format: '$context.requestId'
      MethodSettings:
        - ResourcePath: "/*"
          HttpMethod: "*"
          LoggingLevel: INFO
          DataTraceEnabled: true
```

## Troubleshooting

### Logs Not Appearing in CloudWatch

**Symptom:** API Gateway logs are not appearing in CloudWatch Logs.

**Possible Causes:**
- CloudWatch logging not enabled for the API stage
- Incorrect log level setting
- IAM role not properly configured
- CloudWatch log group doesn't exist

**Solutions:**
1. Verify CloudWatch logging is enabled for the API stage
2. Check log level is set to INFO or ERROR (not OFF)
3. Verify API Gateway account settings show the correct role ARN
4. Check CloudWatch log groups for API Gateway logs
5. Ensure API is receiving traffic to generate logs

### Stack Already Exists Error

**Symptom:** CloudFormation reports stack already exists.

**Cause:** Template was already deployed in this account/region.

**Solution:** This is expected. Only one deployment per account/region is needed. If you need to update the configuration, update the existing stack instead of creating a new one.

### Access Denied When Creating Role

**Symptom:** CloudFormation fails with access denied error.

**Possible Causes:**
- Insufficient IAM permissions
- Permissions boundary restrictions
- Service control policies (SCPs) blocking action

**Solutions:**
1. Verify you have `iam:CreateRole` permission
2. Check for permissions boundaries that might restrict role creation
3. Review SCPs if using AWS Organizations
4. Ensure you have `apigateway:UpdateAccount` permission

### Role Already Exists

**Symptom:** CloudFormation fails because role already exists.

**Cause:** Role was created manually or by another stack.

**Solutions:**
1. Delete the existing role if it's not in use
2. Import the existing role into CloudFormation
3. Use a different stack name if multiple configurations are needed (not recommended)

## Related Templates

This template is used with:

- **Pipeline Templates**: APIs deployed via pipeline templates
  - [template-pipeline.yml](../pipeline/template-pipeline-README.md)
  - [template-pipeline-github.yml](../pipeline/template-pipeline-github-README.md)

- **Network Templates**: APIs with custom domains
  - [template-network-route53-cloudfront-s3-apigw.yml](../network/template-network-route53-cloudfront-s3-apigw-README.md)

- **Application Templates**: Any SAM template with API Gateway resources

## Security Considerations

1. **Least Privilege**: Role uses AWS-managed policy with minimal required permissions
2. **Trust Policy**: Only API Gateway service can assume the role
3. **Account-Level**: Role applies to all APIs in the account
4. **No Secrets**: No sensitive information stored in the role
5. **CloudTrail**: All API Gateway actions logged via CloudTrail

## Cost Considerations

**IAM Costs:**
- IAM roles and policies: No charge

**CloudWatch Logs Costs:**
- Log ingestion: $0.50 per GB
- Log storage: $0.03 per GB per month
- Log retention: Configure retention period to manage costs

**Cost Optimization Tips:**
1. Set appropriate log retention periods (7-30 days for development, 90+ days for production)
2. Use log level INFO or ERROR instead of DEBUG to reduce log volume
3. Enable logging only for production stages
4. Use CloudWatch Logs Insights for efficient log analysis
5. Consider exporting logs to S3 for long-term storage at lower cost

## Best Practices

1. **Deploy Once**: Deploy this template once per account per region
2. **Centralized Management**: Use this role for all API Gateway APIs in the account
3. **Log Retention**: Configure appropriate retention periods for CloudWatch log groups
4. **Monitoring**: Set up CloudWatch alarms for API Gateway errors
5. **Access Control**: Restrict access to CloudWatch log groups using IAM policies

## Additional Resources

- [API Gateway CloudWatch Logging](https://docs.aws.amazon.com/apigateway/latest/developerguide/set-up-logging.html)
- [API Gateway Account Settings](https://docs.aws.amazon.com/apigateway/latest/developerguide/how-to-stage-settings.html)
- [CloudWatch Logs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/)
- [IAM Roles for Services](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-service.html)
- [GitHub Repository](https://github.com/63klabs/atlantis-cfn-template-repo-for-serverless-deployments/)
