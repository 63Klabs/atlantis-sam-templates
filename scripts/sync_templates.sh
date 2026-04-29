#!/bin/bash

# Make script executable
# chmod +x sync_templates.sh

# Basic usage
# ./sync_templates.sh templates my-bucket /atlantis/templates
# ./sync_templates.sh templates my-bucket /atlantis/templates --profile myprofile

# Basic usage with default credentials
# ./sync_templates.sh templates my-bucket /atlantis/templates

# With specific profile
# ./sync_templates.sh templates my-bucket /atlantis/templates --profile myprofile

# With custom source directory
# ./sync_templates.sh templates my-bucket /atlantis/templates --profile myprofile

# Dryrun to preview changes
# ./sync_templates.sh templates my-bucket /atlantis/templates --dryrun

# Full example with all options
# ./sync_templates.sh templates my-bucket /atlantis/templates --profile myprofile --dryrun

set -e  # Exit on error

# Initialize variables
SOURCE_DIR=""
BUCKET_NAME=""
BASE_PATH=""
AWS_PROFILE=""
DRYRUN=""

# Function to show usage
usage() {
    echo "Usage: $0 <source-dir> <bucket-name> <base-path> [--profile profile-name] [--dryrun]"
    echo "Example: $0 templates my-bucket atlantis/templates --profile myprofile"
    echo ""
    echo "Options:"
    echo "  --profile   Specify AWS profile"
    echo "  --dryrun    Show what would be uploaded without actually uploading"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)
            if [[ -z "$2" || "$2" == --* ]]; then
                echo "Error: --profile requires a value"
                exit 1
            fi
            AWS_PROFILE="$2"
            shift 2
            ;;
        --dryrun)
            DRYRUN="--dryrun"
            shift
            ;;
        *)
            # Handle positional arguments
            if [ -z "$SOURCE_DIR" ]; then
                SOURCE_DIR="$1"
            elif [ -z "$BUCKET_NAME" ]; then
                BUCKET_NAME="$1"
            elif [ -z "$BASE_PATH" ]; then
                BASE_PATH="$1"
            else
                echo "Error: Unexpected argument: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Validate required arguments
if [ -z "$SOURCE_DIR" ] || [ -z "$BUCKET_NAME" ] || [ -z "$BASE_PATH" ]; then
    echo "Error: Missing required arguments"
    usage
fi

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory '$SOURCE_DIR' not found"
    exit 1
fi

# Build AWS command with optional profile
AWS_CMD="aws"
if [ -n "$AWS_PROFILE" ]; then
    AWS_CMD="aws --profile $AWS_PROFILE"
    echo "Using AWS profile: $AWS_PROFILE"
else
    # Check if AWS credentials are available
    if ! aws sts get-caller-identity >/dev/null 2>&1; then
        echo "Error: No AWS credentials found. Please either:"
        echo "1. Configure default credentials using 'aws configure'"
        echo "2. Set AWS environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)"
        echo "3. Use --profile option to specify a profile"
        exit 1
    fi
    echo "Using default AWS credentials"
fi

echo "Syncing files from $SOURCE_DIR to s3://${BUCKET_NAME}${BASE_PATH}..."

# Perform the sync operation
$AWS_CMD s3 sync "./$SOURCE_DIR" "s3://${BUCKET_NAME}${BASE_PATH}" \
    --delete \
    --exclude "*" \
    --exclude ".*" \
    --exclude ".*/*" \
    --include "*.zip" \
    --include "*.json" \
    --include "*.yaml" \
    --include "*.yml" \
    $DRYRUN

if [ $? -eq 0 ]; then
    if [ -n "$DRYRUN" ]; then
        echo "Dryrun completed successfully"
    else
        echo "Sync completed successfully"
    fi
else
    echo "Error: Sync failed"
    exit 1
fi

echo "Done!"
