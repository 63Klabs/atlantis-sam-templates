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

# File extensions to include
INCLUDE_EXTENSIONS="zip json yaml yml"

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

# Normalize BASE_PATH: strip leading slash (S3 keys should not start with /)
BASE_PATH="${BASE_PATH#/}"
# Ensure BASE_PATH ends with / if not empty
if [ -n "$BASE_PATH" ] && [[ "$BASE_PATH" != */ ]]; then
    BASE_PATH="${BASE_PATH}/"
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

# Build find arguments for included extensions
FIND_ARGS=()
FIRST=true
for ext in $INCLUDE_EXTENSIONS; do
    if [ "$FIRST" = true ]; then
        FIRST=false
    else
        FIND_ARGS+=("-o")
    fi
    FIND_ARGS+=("-name" "*.$ext")
done

# Counters
UPLOADED=0
SKIPPED=0
FAILED=0
DELETED=0

# Upload local files that have changed (compare by MD5/ETag)
while IFS= read -r LOCAL_FILE; do
    # Get the S3 key by stripping the source directory prefix
    S3_KEY="${BASE_PATH}${LOCAL_FILE#$SOURCE_DIR/}"

    # Calculate local MD5
    LOCAL_MD5=$(md5sum "$LOCAL_FILE" | cut -d' ' -f1)
    LOCAL_ETAG="\"$LOCAL_MD5\""

    # Get remote ETag
    REMOTE_ETAG=$($AWS_CMD s3api head-object \
        --bucket "$BUCKET_NAME" \
        --key "$S3_KEY" \
        --query 'ETag' \
        --output text 2>/dev/null || echo "none")

    if [ "$LOCAL_ETAG" != "$REMOTE_ETAG" ]; then
        if [ -n "$DRYRUN" ]; then
            echo "[DRYRUN] Would upload: $LOCAL_FILE -> s3://${BUCKET_NAME}/${S3_KEY}"
            echo "  Local hash:  $LOCAL_ETAG"
            echo "  Remote hash: $REMOTE_ETAG"
        else
            echo "Uploading: $LOCAL_FILE -> s3://${BUCKET_NAME}/${S3_KEY}"
            if $AWS_CMD s3 cp "$LOCAL_FILE" "s3://${BUCKET_NAME}/${S3_KEY}" > /dev/null; then
                UPLOADED=$((UPLOADED + 1))
            else
                echo "  Error uploading $LOCAL_FILE"
                FAILED=$((FAILED + 1))
            fi
        fi
    else
        SKIPPED=$((SKIPPED + 1))
        echo "Unchanged: $LOCAL_FILE"
    fi
done < <(find "$SOURCE_DIR" -type f \( "${FIND_ARGS[@]}" \) ! -path '*/.*' | sort)

# Delete remote files that no longer exist locally (replicate --delete behavior)
echo ""
echo "Checking for remote files to delete..."

# List all objects under the base path
REMOTE_KEYS=$($AWS_CMD s3api list-objects-v2 \
    --bucket "$BUCKET_NAME" \
    --prefix "${BASE_PATH}" \
    --query 'Contents[].Key' \
    --output text 2>/dev/null || echo "")

if [ -n "$REMOTE_KEYS" ] && [ "$REMOTE_KEYS" != "None" ]; then
    for REMOTE_KEY in $REMOTE_KEYS; do
        # Check if the extension is one we manage
        REMOTE_EXT="${REMOTE_KEY##*.}"
        MANAGED=false
        for ext in $INCLUDE_EXTENSIONS; do
            if [ "$REMOTE_EXT" = "$ext" ]; then
                MANAGED=true
                break
            fi
        done

        if [ "$MANAGED" = false ]; then
            continue
        fi

        # Reconstruct the expected local path
        LOCAL_PATH="${SOURCE_DIR}/${REMOTE_KEY#$BASE_PATH}"

        if [ ! -f "$LOCAL_PATH" ]; then
            if [ -n "$DRYRUN" ]; then
                echo "[DRYRUN] Would delete: s3://${BUCKET_NAME}/${REMOTE_KEY}"
            else
                echo "Deleting: s3://${BUCKET_NAME}/${REMOTE_KEY}"
                if $AWS_CMD s3 rm "s3://${BUCKET_NAME}/${REMOTE_KEY}" > /dev/null; then
                    DELETED=$((DELETED + 1))
                else
                    echo "  Error deleting s3://${BUCKET_NAME}/${REMOTE_KEY}"
                    FAILED=$((FAILED + 1))
                fi
            fi
        fi
    done
fi

# Summary
echo ""
echo "--- Sync Summary ---"
if [ -n "$DRYRUN" ]; then
    echo "Mode: DRYRUN (no changes made)"
fi
echo "Uploaded: $UPLOADED"
echo "Skipped:  $SKIPPED"
echo "Deleted:  $DELETED"
if [ "$FAILED" -gt 0 ]; then
    echo "Failed:   $FAILED"
    echo "Error: Some operations failed"
    exit 1
fi
echo "Done!"
