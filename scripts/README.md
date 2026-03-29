# Scripts Directory

This directory contains utility scripts for managing AWS CloudFormation templates using a template and module S3 bucket.

## Prerequisites for Deployments

### Manual from CLI

Before using these scripts locally, ensure you have the following installed:

- Python 3.13+
- AWS CLI configured with appropriate credentials
- Required Python packages from `requirements.txt`

```bash
pip install -r requirements.txt
```

Make scripts executable (if you plan in executing from your machine):

```bash
chmod +x ./scripts/*.{sh,py}
```

Commands to execute the scripts are included in the `post_build` section of the [buildspec.yml](../buildspec.yml) file and can be used for manual deployments if you set the following environment variables in your terminal:

```bash
export AWS_PROFILE="your-profile" # if not using default so you don't need to set --profile flag after commands
export SOURCE_DIR="templates"
export S3_HOST_BASE_PATH="/atlantis/" # Must be single / or begin and end with / (suggested: /atlantis/)
export S3_HOST_BUCKET="s3-bucket-name"
export DRYRUN="" # set to "--dryrun" if performing dry runs
```

### Manual using Docker and CodeBuild Agent

You can also utilize Docker and run the buildspec file directly. See [AWS Documentation: Run builds locally with the AWS CodeBuild agent](https://docs.aws.amazon.com/codebuild/latest/userguide/use-codebuild-agent.html).

Ensure the `HOST_BUCKET` environment variables are set (all others are set in the buildspec `env.variables` section).

### Automated Deployment using AWS CodePipeline using CodeBuild

The buildspec file can be used for automated deployments and expects `HOST_BUCKET` and `DEPLOY_ENV` to be already set in the CodeBuild environment.

Recommended Pipeline Template: [templates/v2/pipeline/template-pipeline-build-only](../templates/v2/pipeline/template-pipeline-build-only.yml)

### Automated Deployment using GitHub Actions

The [.github/workflows/deploy.yml](../.github/workflows/deploy.yml) can be used with GitHub Actions.

You will need to add a github-actions-service IAM role to your account granting access for your repository to copy files to S3.

Set the following GitHub Actions secrets and variables for your repository:

- Secrets:
  - `AWS_RELEASE_ACCT`
  - `AWS_RELEASE_REGION`
- Variables:
  - `AWS_RELEASE_BUCKET` : bucket to upload artifact to
  - `AWS_RELEASE_BUCKET_UTILS_PATH` : Must be single `/` or begin and end with `/` (suggested: `/atlantis/utilities/v2/`)
  - `AWS_RELEASE_BUCKET_TEMPLATES_PATH` : Must be single `/` or begin and end with `/` (suggested: `/atlantis/templates/`) (`v2` is already in source path)

## Deployment Scripts

### upload_scripts.sh

Uploads script files to S3 with content-based change detection.

Usage:

```bash
# Basic usage
./scripts/upload_scripts.sh <bucket-name> <base-path>

# With custom source directory
./scripts/upload_scripts.sh <bucket-name> <base-path> <source-dir>

# With AWS profile
./scripts/upload_scripts.sh <bucket-name> <base-path> --profile <profile-name>

# Preview changes with dryrun
./scripts//upload_scripts.sh <bucket-name> <base-path> --dryrun
```

Example Output:

```text
Creating zip file from scripts...
  adding: scripts/requirements.txt (stored 0%)
  adding: scripts/s3_inventory.py (deflated 70%)
  adding: scripts/upload_scripts.sh (deflated 58%)
Local file hash: "903df56da392a3d7945a73f951cdff44"
Checking if file exists in S3...
Remote file hash: none
File has changed, uploading to S3...
Upload successful
Done!
```

### sync_templates.sh

Synchronizes template files with S3, maintaining exact timestamps and handling deletions.

Usage:

```bash
# Basic usage
./scripts/sync_templates.sh <bucket-name> <base-path>

# With custom source directory
./scripts/sync_templates.sh <bucket-name> <base-path> <source-dir>

# With AWS profile
./scripts/sync_templates.sh <bucket-name> <base-path> --profile <profile-name>

# Preview changes with dryrun
./scripts/sync_templates.sh <bucket-name> <base-path> --dryrun
```

Example Output:

```text
Using default AWS credentials
Syncing files from templates to s3://my-bucket/atlantis/utilities...
upload: templates/example.yaml to s3://my-bucket/atlantis/utilities/templates/example.yaml
upload: templates/config.json to s3://my-bucket/atlantis/utilities/templates/config.json
delete: s3://my-bucket/atlantis/utilities/templates/old-file.yml
Sync completed successfully
Done!
```

### s3_inventory.py

Generates an inventory of S3 objects and their metadata.

Usage:

```bash
# Basic usage
python ./scripts/s3_inventory.py --bucket <bucket-name> --prefix <prefix>

# With AWS profile
python ./scripts/s3_inventory.py --bucket <bucket-name> --prefix <prefix> --profile <profile-name>

# Save output to specific location
python ./scripts/s3_inventory.py --bucket <bucket-name> --prefix <prefix> --output ./outputs/inventory.json
```

Example Output:

```json
{
  "bucket": "XXXXXXXXX",
  "prefix": "atlantis/utilities",
  "objects": [
    {
      "key": "atlantis/utilities/templates/example.yaml",
      "size": 1234,
      "last_modified": "2024-01-20T15:30:00Z",
      "etag": "\"abc123def456\""
    },
    {
      "key": "atlantis/utilities/scripts/template_scripts.zip",
      "size": 5678,
      "last_modified": "2024-01-20T15:35:00Z",
      "etag": "\"xyz789\""
    }
  ]
}
```

### Common Script Options

All scripts support the following common options:

- `--profile`: Specify an AWS profile to use
- `--dryrun`: Preview changes without making them (s3_inventory.py does not support this as it does not modify S3)

### Script Error Handling

Scripts will exit with appropriate error messages for common issues:

- Missing AWS credentials
- Invalid parameters
- File/directory not found
- S3 access denied
- Network connectivity issues

## Requirements

See requirements.txt for Python package dependencies:

```text
boto3>=1.26.0
botocore>=1.29.0
```

## Notes

- All scripts use AWS credentials from either:
  - Default profile
  - Specified profile via `--profile`
  - Environment variables (`AWS_PROFILE`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- Scripts maintain consistent behavior across different operating systems
- File timestamps and checksums are used to minimize unnecessary uploads and S3 versions

This README and the scripts contained within this directory were generated by Amazon Q through iterative prompts and testing by the author to produce the desired results. 

Report any bugs or security issues via the [Atlantis template repository for serverless deployments using AWS SAM and CloudFormation](https://github.com/63Klabs/atlantis-sam-templates) repository.
