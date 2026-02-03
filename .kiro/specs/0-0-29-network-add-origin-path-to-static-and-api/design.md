# Design Document

## Overview

This design adds two new optional parameters (`StaticOriginPath` and `ApiOriginPath`) to the CloudFront network template, allowing users to customize the origin paths used by CloudFront when fetching content from S3 and API Gateway origins. The design maintains full backward compatibility by defaulting to the current hardcoded paths when the parameters are left empty.

The implementation uses CloudFormation conditions to select between three cases for each origin:
1. Empty parameter (default) → Use current default path with substitutions
2. Single `/` → Use empty string (root path)
3. Custom path → Use the provided path as-is

## Architecture

### Parameter Addition

Two new parameters will be added to the template's Parameters section:

- **StaticOriginPath**: Controls the origin path for the S3 static content origin
- **ApiOriginPath**: Controls the origin path for the API Gateway origin

Both parameters will:
- Default to empty string (maintaining current behavior)
- Accept paths starting with `/`
- Reject paths ending with `/` (except single `/`)
- Reject placeholder syntax like `{StageId}` or `${StageId}`
- Be placed in the "Origins for S3 and/or API Gateway" parameter group

### Conditional Logic

The design introduces new conditions to handle the three cases for each origin path:

**For Static Origin:**
- `StaticOriginPathIsEmpty`: True when `StaticOriginPath` equals empty string
- `StaticOriginPathIsRoot`: True when `StaticOriginPath` equals `/`
- `UseDefaultStaticOriginPath`: True when `StaticOriginPathIsEmpty` is true
- `UseRootStaticOriginPath`: True when `StaticOriginPathIsRoot` is true
- `UseCustomStaticOriginPath`: True when neither empty nor `/`

**For API Origin:**
- `ApiOriginPathIsEmpty`: True when `ApiOriginPath` equals empty string
- `ApiOriginPathIsRoot`: True when `ApiOriginPath` equals `/`
- `UseDefaultApiOriginPath`: True when `ApiOriginPathIsEmpty` is true
- `UseRootApiOriginPath`: True when `ApiOriginPathIsRoot` is true
- `UseCustomApiOriginPath`: True when neither empty nor `/`

### Resource Modifications

The `CloudFrontDistribution` resource will be modified to use conditional logic for the `OriginPath` property of both origins:

**Static S3 Origin:**
```yaml
OriginPath: !If
  - UseDefaultStaticOriginPath
  - !Sub "/${StageId}/public"
  - !If
    - UseRootStaticOriginPath
    - ""
    - !Ref StaticOriginPath
```

**API Gateway Origin:**
```yaml
OriginPath: !If
  - UseDefaultApiOriginPath
  - !Sub "/${ProjectId}-${StageId}"
  - !If
    - UseRootApiOriginPath
    - ""
    - !Ref ApiOriginPath
```

## Components and Interfaces

### Parameters

#### StaticOriginPath

**Type:** String  
**Default:** `""` (empty string)  
**Description:** Custom origin path for static S3 content. Leave empty to use default `/${StageId}/public`. Use `/` for root path (no prefix). Use `/custom/path` for a custom path. Path must start with `/` and not end with `/` (except single `/`). Do not use placeholder syntax like `{StageId}`.

**AllowedPattern:** `^$|^\/$|^\/[a-zA-Z0-9\/_-]+[^\/]$`

**Validation Rules:**
- Empty string is allowed (default behavior)
- Single `/` is allowed (root path)
- Must start with `/` if not empty
- Must not end with `/` unless it's exactly `/`
- Must not contain `{` or `}` characters
- Can contain alphanumeric characters, forward slashes, hyphens, and underscores

**ConstraintDescription:** Must be empty (default), `/` (root), or a path starting with `/` and not ending with `/`. Valid examples: `/static`, `/v1/content`, `/app/public`. Do not use placeholders like `{StageId}`.

#### ApiOriginPath

**Type:** String  
**Default:** `""` (empty string)  
**Description:** Custom origin path for API Gateway. Leave empty to use default `/${ProjectId}-${StageId}`. Use `/` for root path (no prefix). Use `/custom/path` for a custom path. Path must start with `/` and not end with `/` (except single `/`). Do not use placeholder syntax like `{StageId}`.

**AllowedPattern:** `^$|^\/$|^\/[a-zA-Z0-9\/_-]+[^\/]$`

**Validation Rules:**
- Empty string is allowed (default behavior)
- Single `/` is allowed (root path)
- Must start with `/` if not empty
- Must not end with `/` unless it's exactly `/`
- Must not contain `{` or `}` characters
- Can contain alphanumeric characters, forward slashes, hyphens, and underscores

**ConstraintDescription:** Must be empty (default), `/` (root), or a path starting with `/` and not ending with `/`. Valid examples: `/api`, `/v2/services`, `/prod`. Do not use placeholders like `{StageId}`.

### Conditions

The following conditions will be added to the Conditions section:

```yaml
# Static Origin Path Conditions
StaticOriginPathIsEmpty: !Equals [!Ref StaticOriginPath, ""]
StaticOriginPathIsRoot: !Equals [!Ref StaticOriginPath, "/"]
UseDefaultStaticOriginPath: !Condition StaticOriginPathIsEmpty
UseRootStaticOriginPath: !And
  - !Not [!Condition StaticOriginPathIsEmpty]
  - !Condition StaticOriginPathIsRoot
UseCustomStaticOriginPath: !And
  - !Not [!Condition StaticOriginPathIsEmpty]
  - !Not [!Condition StaticOriginPathIsRoot]

# API Origin Path Conditions
ApiOriginPathIsEmpty: !Equals [!Ref ApiOriginPath, ""]
ApiOriginPathIsRoot: !Equals [!Ref ApiOriginPath, "/"]
UseDefaultApiOriginPath: !Condition ApiOriginPathIsEmpty
UseRootApiOriginPath: !And
  - !Not [!Condition ApiOriginPathIsEmpty]
  - !Condition ApiOriginPathIsRoot
UseCustomApiOriginPath: !And
  - !Not [!Condition ApiOriginPathIsEmpty]
  - !Not [!Condition ApiOriginPathIsRoot]
```

### CloudFront Distribution Origin Configuration

The Origins section of the CloudFrontDistribution resource will be updated to use the conditional logic:

**Static S3 Origin (when HasStaticOrigin is true):**
```yaml
- DomainName: !Ref S3OriginDomainName
  Id: StaticS3Origin
  OriginAccessControlId: !Ref CloudFrontOriginAccessControl
  OriginPath: !If
    - UseDefaultStaticOriginPath
    - !Sub "/${StageId}/public"
    - !If
      - UseRootStaticOriginPath
      - ""
      - !Ref StaticOriginPath
  S3OriginConfig:
    OriginAccessIdentity: ''
```

**API Gateway Origin (when ApiIsBehindCloudFront is true):**
```yaml
- DomainName: !Sub "${ApiGatewayId}.execute-api.${AWS::Region}.amazonaws.com"
  Id: ApiGatewayOrigin
  OriginPath: !If
    - UseDefaultApiOriginPath
    - !Sub "/${ProjectId}-${StageId}"
    - !If
      - UseRootApiOriginPath
      - ""
      - !Ref ApiOriginPath
  CustomOriginConfig:
    HTTPSPort: 443
    OriginProtocolPolicy: https-only
    OriginSSLProtocols:
      - TLSv1.2
```

### Output Updates

The following outputs will be updated to reflect the actual origin paths used:

**S3Origin Output:**
```yaml
S3Origin: 
  Condition: HasStaticOrigin
  Description: S3 Origin with path.
  Value: !Sub
    - "${S3OriginDomainName}${OriginPath}"
    - OriginPath: !If
        - UseDefaultStaticOriginPath
        - !Sub "/${StageId}/public"
        - !If
          - UseRootStaticOriginPath
          - ""
          - !Ref StaticOriginPath
```

**ApiGatewayOrigin Output:**
```yaml
ApiGatewayOrigin:
  Condition: HasApiGatewayOrigin
  Description: API Gateway Origin with path.
  Value: !Sub
    - "${ApiGatewayId}.execute-api.${AWS::Region}.amazonaws.com${OriginPath}"
    - OriginPath: !If
        - UseDefaultApiOriginPath
        - !Sub "/${ProjectId}-${StageId}"
        - !If
          - UseRootApiOriginPath
          - ""
          - !Ref ApiOriginPath
```

## Data Models

### Parameter Values

**StaticOriginPath and ApiOriginPath accept three types of values:**

1. **Empty String (Default):**
   - Input: `""`
   - Behavior: Use template's default path with variable substitution
   - Static Result: `/${StageId}/public`
   - API Result: `/${ProjectId}-${StageId}`

2. **Root Path:**
   - Input: `"/"`
   - Behavior: Use empty string for CloudFront (no path prefix)
   - Result: `""` (empty string in CloudFront configuration)

3. **Custom Path:**
   - Input: `/custom/path` (any valid path)
   - Behavior: Use the provided path as-is
   - Result: The exact input value (e.g., `/custom/path`)

### Validation Constraints

**Path Format Rules:**
- Must be empty, `/`, or start with `/`
- Must not end with `/` unless it's exactly `/`
- Must not contain `{` or `}` characters (prevents placeholder usage)
- Can contain: alphanumeric characters, forward slashes, hyphens, underscores
- Maximum length: 255 characters (CloudFormation string limit)

**Regex Pattern:** `^$|^\/$|^\/[a-zA-Z0-9\/_-]+[^\/]$`

**Pattern Breakdown:**
- `^$` - Matches empty string
- `|` - OR
- `^\/$` - Matches exactly `/`
- `|` - OR
- `^\/[a-zA-Z0-9\/_-]+[^\/]$` - Matches paths starting with `/`, containing valid characters, not ending with `/`

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*


### Property 1: Default Static Origin Path

*For any* valid StageId value, when StaticOriginPath is empty (default), the resulting CloudFront origin path should equal `/${StageId}/public`

**Validates: Requirements 1.2, 4.1**

### Property 2: Default API Origin Path

*For any* valid ProjectId and StageId values, when ApiOriginPath is empty (default), the resulting CloudFront origin path should equal `/${ProjectId}-${StageId}`

**Validates: Requirements 2.2, 4.4**

### Property 3: Custom Static Origin Path Passthrough

*For any* valid custom path (not empty, not `/`), when StaticOriginPath is set to that path, the resulting CloudFront origin path should equal the input path exactly

**Validates: Requirements 1.4, 4.3**

### Property 4: Custom API Origin Path Passthrough

*For any* valid custom path (not empty, not `/`), when ApiOriginPath is set to that path, the resulting CloudFront origin path should equal the input path exactly

**Validates: Requirements 2.4, 4.6**

### Property 5: Path Validation Rejects Invalid Formats

*For any* path that does not match the validation rules (doesn't start with `/`, ends with `/` except single `/`, or contains `{` or `}` characters), the template parameter validation should reject the value

**Validates: Requirements 1.5, 1.6, 1.7, 2.5, 2.6, 2.7, 3.2, 3.3, 3.4**

### Property 6: Backward Compatibility

*For any* valid ProjectId and StageId values, when both StaticOriginPath and ApiOriginPath are empty (default), the resulting origin paths should match the previous template version's hardcoded values

**Validates: Requirements 5.1**

## Error Handling

### Parameter Validation Errors

When users provide invalid path values, CloudFormation will reject the stack creation/update with a constraint violation error. The error message will include the ConstraintDescription text, which provides:

1. Explanation of valid path formats
2. Examples of valid paths
3. Reminder not to use placeholder syntax

**Example Error Message:**
```
Parameter validation failed: Parameter 'StaticOriginPath' failed to satisfy constraint: 
Must be empty (default), `/` (root), or a path starting with `/` and not ending with `/`. 
Valid examples: `/static`, `/v1/content`, `/app/public`. Do not use placeholders like `{StageId}`.
```

### Invalid Path Formats

The AllowedPattern regex will catch these common errors:

1. **Missing leading slash:** `static` → Rejected
2. **Trailing slash:** `/static/` → Rejected (except `/`)
3. **Placeholder syntax:** `/${StageId}/public` → Rejected
4. **Curly braces:** `/path/{id}` → Rejected
5. **Invalid characters:** `/path with spaces` → Rejected

### CloudFront Configuration Errors

If a user provides a path that passes validation but causes CloudFront configuration issues (e.g., path doesn't exist in S3), CloudFormation will fail during resource creation with a CloudFront-specific error. This is expected behavior and not something the template can prevent.

## Testing Strategy

This feature will be tested using a dual approach combining unit tests and property-based tests.

### Unit Tests

Unit tests will verify specific examples and edge cases:

1. **Template Structure Tests:**
   - Verify StaticOriginPath parameter exists with correct properties
   - Verify ApiOriginPath parameter exists with correct properties
   - Verify parameters are in correct metadata group
   - Verify parameters have correct AllowedPattern regex
   - Verify parameters have helpful ConstraintDescription text

2. **Edge Case Tests:**
   - Test root path (`/`) produces empty string for both origins
   - Test empty string produces default paths
   - Test specific custom paths are used as-is

3. **Validation Tests:**
   - Test regex pattern rejects paths without leading `/`
   - Test regex pattern rejects paths with trailing `/` (except `/`)
   - Test regex pattern rejects paths with `{` or `}` characters
   - Test regex pattern accepts valid custom paths

### Property-Based Tests

Property-based tests will verify universal properties across many generated inputs. Each test will run a minimum of 100 iterations.

1. **Property Test: Default Static Origin Path**
   - Generate random valid StageId values
   - Set StaticOriginPath to empty string
   - Verify origin path equals `/${StageId}/public`
   - **Tag:** Feature: 0-0-29-network-add-origin-path-to-static-and-api, Property 1: Default Static Origin Path

2. **Property Test: Default API Origin Path**
   - Generate random valid ProjectId and StageId values
   - Set ApiOriginPath to empty string
   - Verify origin path equals `/${ProjectId}-${StageId}`
   - **Tag:** Feature: 0-0-29-network-add-origin-path-to-static-and-api, Property 2: Default API Origin Path

3. **Property Test: Custom Static Origin Path Passthrough**
   - Generate random valid custom paths
   - Set StaticOriginPath to generated path
   - Verify origin path equals the input path exactly
   - **Tag:** Feature: 0-0-29-network-add-origin-path-to-static-and-api, Property 3: Custom Static Origin Path Passthrough

4. **Property Test: Custom API Origin Path Passthrough**
   - Generate random valid custom paths
   - Set ApiOriginPath to generated path
   - Verify origin path equals the input path exactly
   - **Tag:** Feature: 0-0-29-network-add-origin-path-to-static-and-api, Property 4: Custom API Origin Path Passthrough

5. **Property Test: Path Validation Rejects Invalid Formats**
   - Generate random invalid paths (missing `/`, trailing `/`, with `{}`}`)
   - Attempt to validate against AllowedPattern
   - Verify all invalid paths are rejected
   - **Tag:** Feature: 0-0-29-network-add-origin-path-to-static-and-api, Property 5: Path Validation Rejects Invalid Formats

6. **Property Test: Backward Compatibility**
   - Generate random valid ProjectId and StageId values
   - Set both origin paths to empty string
   - Verify static origin path equals `/${StageId}/public`
   - Verify API origin path equals `/${ProjectId}-${StageId}`
   - **Tag:** Feature: 0-0-29-network-add-origin-path-to-static-and-api, Property 6: Backward Compatibility

### Testing Library

For Python-based testing, we will use:
- **pytest** for test framework
- **hypothesis** for property-based testing (already in project dependencies)
- **pyyaml** for CloudFormation template parsing
- **re** (standard library) for regex validation testing

### Test Configuration

- Minimum 100 iterations per property test
- Each property test references its design document property number
- Tests are organized in `tests/test_network_template_property.py` (property tests) and `tests/test_network_template_unit.py` (unit tests)
