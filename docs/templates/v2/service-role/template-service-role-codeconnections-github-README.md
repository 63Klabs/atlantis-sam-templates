# template-service-role-codeconnections-github.yml

GitHub connection for CodePipeline source integration via AWS CodeConnections.

**Version:** Not versioned (connection resource)  
**Last Updated:** N/A  
**Template:** [templates/v2/service-role/template-service-role-codeconnections-github.yml](../../../../templates/v2/service-role/template-service-role-codeconnections-github.yml)

## Overview

This template creates an AWS CodeConnections connection to GitHub, enabling CodePipeline to access GitHub repositories for automated deployments. The connection requires manual authorization in the AWS Console after deployment.

### Key Features

- **GitHub Integration**: Direct connection to GitHub organizations or personal accounts
- **Secure OAuth**: Uses OAuth for secure authentication with GitHub
- **Manual Authorization**: Requires one-time manual authorization in AWS Console
- **Retained on Deletion**: Connection is retained when stack is deleted
- **Reusable**: One connection can be used by multiple pipelines
- **Organization Support**: Works with GitHub organizations and personal accounts

### Use Cases

- Connect CodePipeline to GitHub repositories
- Enable automated deployments from GitHub
- Secure GitHub organization access for CI/CD
- Multi-repository deployments from single GitHub organization
- Open source projects with public GitHub repositories

### Prerequisites

- GitHub organization or personal account
- Admin permissions in GitHub organization (for authorization)
- AWS account with permissions to create CodeConnections
- No other prerequisites

> **Important:** Manual completion required after deployment. The connection will be in "PENDING" status until you authorize it in the AWS Console.

## Parameters

### Application Resource Naming

Parameters for naming the connection resource.

- [Prefix](#prefix)
- [GitHubOrg](#githuborg)

#### Prefix

Prefix prepended to the connection name for namespace identification.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | acme |
| Allowed Pattern | `^[a-z][a-z0-9-]{0,6}[a-z0-9]$` |
| Min Length | 2 |
| Max Length | 8 |
| Constraint Description | 2 to 8 characters. Lower case alphanumeric and dashes. Must start with a letter and end with a letter or number. |

Short, descriptive 2-6 character values work best. Connection is named `<Prefix>-<GitHubOrg>-github-connection`.

#### GitHubOrg

GitHub organization or username to connect to.

| Attribute | Setting |
|-----------|---------|
| Type | String |
| Default | None |
| Min Length | 1 |
| Constraint Description | Must be a valid GitHub organization or username |

This is the GitHub organization name or personal username that will be connected. For example, "mycompany" or "myusername".

## Resources

This template creates the following resource:

- [GitHubConnection](#githubconnection) - AWS::CodeConnections::Connection

### GitHubConnection

Type: AWS::CodeConnections::Connection  
Deletion Policy: Retain  
Update/Replace Policy: Retain

AWS CodeConnections connection to GitHub.

**Key Properties:**
- **ConnectionName**: `${Prefix}-${GitHubOrg}-github-connection`
- **ProviderType**: GitHub
- **Initial Status**: PENDING (requires manual authorization)
- **Retention**: Retained on stack deletion
- **Tags**: Includes GitHubOrg tag for identification

**Connection Lifecycle:**
1. **PENDING**: Initial state after creation, requires authorization
2. **AVAILABLE**: Active state after manual authorization
3. **ERROR**: Failed state if authorization fails or is revoked

> **Important:** The connection is retained when the CloudFormation stack is deleted. This prevents accidental deletion of connections used by multiple pipelines. You must manually delete the connection in the AWS Console if no longer needed.

## Outputs

### ConnectionArn

ARN of the GitHub connection.

**Value:** ARN of GitHubConnection

**Usage:** Use this ARN in pipeline templates (GitHubConnectionArn parameter) to connect CodePipeline to GitHub repositories.

**Example Value:** `arn:aws:codeconnections:us-east-1:123456789012:connection/abc123-def456-ghi789`

> **Note:** You must manually complete the connection in the AWS Console before using this ARN in pipeline templates.

### ConnectionStatus

Current status of the GitHub connection.

**Value:** Connection status (PENDING, AVAILABLE, or ERROR)

**Usage:** Check this output to verify if the connection has been authorized.

**Possible Values:**
- `PENDING`: Connection created but not yet authorized
- `AVAILABLE`: Connection authorized and ready to use
- `ERROR`: Connection authorization failed or was revoked

### ConsoleUrl

URL to complete the connection setup in the AWS Console.

**Value:** `https://${AWS::Region}.console.aws.amazon.com/codesuite/settings/connections`

**Usage:** Navigate to this URL to find and authorize the connection.

## Manual Authorization Steps

After deploying this template, you must manually authorize the connection:

### Step 1: Navigate to AWS Console

Use the ConsoleUrl output from the stack to navigate to the CodeConnections console:

```bash
# Get the console URL from stack outputs
aws cloudformation describe-stacks \
  --stack-name github-connection \
  --query 'Stacks[0].Outputs[?OutputKey==`ConsoleUrl`].OutputValue' \
  --output text
```

### Step 2: Find Your Connection

1. In the AWS Console, go to **Developer Tools** → **Settings** → **Connections**
2. Find your connection (named `${Prefix}-${GitHubOrg}-github-connection`)
3. Status will show as **Pending**

### Step 3: Authorize Connection

1. Click on the connection name
2. Click **Update pending connection** button
3. Click **Install a new app** (or select existing GitHub App)
4. You'll be redirected to GitHub
5. Select the GitHub organization
6. Click **Install** or **Authorize**
7. You'll be redirected back to AWS Console
8. Connection status changes to **Available**

### Step 4: Verify Connection

```bash
# Check connection status
aws codeconnections get-connection \
  --connection-arn <connection-arn> \
  --query 'Connection.ConnectionStatus' \
  --output text

# Expected output: AVAILABLE
```

## Examples

### Basic Deployment

```bash
# Deploy using AWS CLI
aws cloudformation create-stack \
  --stack-name github-connection \
  --template-body file://template-service-role-codeconnections-github.yml \
  --parameters \
    ParameterKey=Prefix,ParameterValue=acme \
    ParameterKey=GitHubOrg,ParameterValue=mycompany \
  --region us-east-1
```

### Deployment using SAM CLI

```bash
# Deploy using SAM CLI
sam deploy \
  --template-file template-service-role-codeconnections-github.yml \
  --stack-name github-connection \
  --parameter-overrides \
    Prefix=acme \
    GitHubOrg=mycompany \
  --region us-east-1
```

### Using Connection in Pipeline

After authorization, use the connection ARN in your pipeline template:

```yaml
Parameters:
  GitHubConnectionArn:
    Type: String
    Default: "arn:aws:codeconnections:us-east-1:123456789012:connection/abc123-def456"

Resources:
  Pipeline:
    Type: AWS::CodePipeline::Pipeline
    Properties:
      Stages:
        - Name: Source
          Actions:
            - Name: SourceAction
              ActionTypeId:
                Category: Source
                Owner: AWS
                Provider: CodeStarSourceConnection
                Version: 1
              Configuration:
                ConnectionArn: !Ref GitHubConnectionArn
                FullRepositoryId: mycompany/my-repo
                BranchName: main
```

## Troubleshooting

### Connection Stuck in PENDING Status

**Symptom:** Connection remains in PENDING status after deployment.

**Cause:** Connection has not been manually authorized.

**Solution:** Follow the manual authorization steps above to complete the connection setup.

### Authorization Fails

**Symptom:** Authorization process fails or returns error.

**Possible Causes:**
- Insufficient permissions in GitHub organization
- GitHub App not installed
- Network connectivity issues
- Browser blocking pop-ups

**Solutions:**
1. Verify you have admin permissions in the GitHub organization
2. Ensure GitHub App is installed in the organization
3. Check network connectivity and firewall settings
4. Allow pop-ups from AWS Console
5. Try using a different browser

### Connection Shows ERROR Status

**Symptom:** Connection status changes to ERROR.

**Possible Causes:**
- GitHub authorization was revoked
- GitHub App was uninstalled
- GitHub organization was deleted
- Connection was manually deleted in GitHub

**Solutions:**
1. Re-authorize the connection in AWS Console
2. Reinstall the GitHub App in GitHub organization
3. Create a new connection if organization was deleted
4. Check GitHub App settings in GitHub organization

### Cannot Find Connection in Console

**Symptom:** Connection not visible in AWS Console.

**Possible Causes:**
- Wrong AWS region selected
- Stack deployment failed
- Insufficient permissions to view connections

**Solutions:**
1. Verify you're in the correct AWS region
2. Check CloudFormation stack status
3. Verify IAM permissions include `codeconnections:ListConnections`

### Pipeline Fails to Access GitHub

**Symptom:** Pipeline fails with "Unable to access repository" error.

**Possible Causes:**
- Connection not authorized (PENDING status)
- Connection ARN incorrect in pipeline
- Repository doesn't exist or is private
- GitHub App doesn't have access to repository

**Solutions:**
1. Verify connection status is AVAILABLE
2. Check connection ARN matches in pipeline configuration
3. Verify repository exists and is accessible
4. Check GitHub App has access to the repository in GitHub settings

## Related Templates

This template is used with:

- **Pipeline Templates**: GitHub-based pipelines
  - [template-pipeline-github.yml](../pipeline/template-pipeline-github-README.md)

- **Application Templates**: Any application deployed from GitHub

## Security Considerations

1. **OAuth Authentication**: Uses secure OAuth for GitHub authentication
2. **Least Privilege**: Connection only has access to repositories authorized in GitHub
3. **Organization Control**: GitHub organization admins control which repositories are accessible
4. **Audit Trail**: All connection usage logged via CloudTrail
5. **Revocable**: Connection can be revoked at any time in GitHub or AWS Console
6. **Retention Policy**: Connection retained on stack deletion to prevent accidental removal

## GitHub Permissions

The GitHub App created by AWS CodeConnections requests the following permissions:

**Repository Permissions:**
- **Contents**: Read access to repository contents
- **Metadata**: Read access to repository metadata
- **Webhooks**: Manage webhooks for pipeline triggers

**Organization Permissions:**
- **Members**: Read access to organization members (for authorization)

> **Note:** You can review and modify these permissions in your GitHub organization settings under **Settings** → **GitHub Apps** → **AWS Connector for GitHub**.

## Cost Considerations

**AWS Costs:**
- CodeConnections: No charge for the connection itself
- CodePipeline: $1 per active pipeline per month (when using the connection)

**GitHub Costs:**
- No additional GitHub costs for using AWS CodeConnections
- Standard GitHub pricing applies for repository hosting

## Best Practices

1. **One Connection Per Organization**: Create one connection per GitHub organization, reuse across multiple pipelines
2. **Descriptive Naming**: Use clear prefix and organization names for easy identification
3. **Access Control**: Limit GitHub App access to only required repositories
4. **Regular Review**: Periodically review connection usage and access
5. **Documentation**: Document which pipelines use which connections
6. **Backup**: Keep connection ARNs documented for disaster recovery

## Additional Resources

- [AWS CodeConnections Documentation](https://docs.aws.amazon.com/codeconnections/latest/userguide/)
- [GitHub Apps Documentation](https://docs.github.com/en/developers/apps)
- [CodePipeline with GitHub](https://docs.aws.amazon.com/codepipeline/latest/userguide/connections-github.html)
- [GitHub Repository](https://github.com/63Klabs/atlantis-sam-templates/)
