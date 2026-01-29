# Design Document

## Overview

The CloudFormation Template Linter system provides automated validation of all CloudFormation templates in the templates/v2 directory structure. The system consists of a Python-based template discovery mechanism, cfn-lint integration, and dual execution modes for both local development and CI/CD pipeline environments. The solution uses a .venv virtual environment for dependency isolation and integrates seamlessly with the existing pytest-based testing infrastructure.

## Architecture

The system follows a modular architecture with clear separation of concerns:

```
CFN Template Linter System
├── Template Discovery Engine
│   ├── File System Scanner
│   └── Template Filter
├── Validation Engine  
│   ├── CFN-Lint Wrapper
│   └── Error Aggregator
├── Execution Modes
│   ├── Local Test Integration (pytest)
│   └── Build Pipeline Integration (buildspec)
└── Virtual Environment Manager
    ├── Dependency Isolation (.venv)
    └── Environment Setup
```

The architecture supports two primary execution paths:
1. **Local Development Path**: Integrated with pytest for developer testing
2. **CI/CD Pipeline Path**: Integrated with buildspec for automated validation

## Components and Interfaces

### Template Discovery Engine

**Purpose**: Recursively discovers CloudFormation template files in the templates/v2 directory structure.

**Interface**:
```python
class TemplateDiscovery:
    def find_templates(self, base_path: str) -> List[Path]
    def is_cloudformation_template(self, file_path: Path) -> bool
```

**Responsibilities**:
- Scan templates/v2 directory recursively
- Identify CloudFormation template files (*.yml, *.yaml extensions)
- Filter out non-template files (README.md, etc.)
- Return list of template file paths for validation

### Validation Engine

**Purpose**: Executes cfn-lint validation on discovered templates and aggregates results.

**Interface**:
```python
class CFNValidator:
    def validate_template(self, template_path: Path) -> ValidationResult
    def validate_all_templates(self, template_paths: List[Path]) -> ValidationSummary
    
class ValidationResult:
    template_path: Path
    is_valid: bool
    errors: List[str]
    warnings: List[str]

class ValidationSummary:
    total_templates: int
    valid_templates: int
    failed_templates: int
    results: List[ValidationResult]
```

**Responsibilities**:
- Execute cfn-lint on individual templates
- Capture validation errors and warnings
- Aggregate results across all templates
- Provide detailed error reporting

### Virtual Environment Manager

**Purpose**: Manages .venv virtual environment for cfn-lint dependency isolation.

**Interface**:
```python
class VirtualEnvManager:
    def ensure_venv_exists(self) -> bool
    def install_dependencies(self) -> bool
    def get_cfn_lint_path(self) -> str
```

**Responsibilities**:
- Create .venv directory if it doesn't exist
- Install cfn-lint and dependencies in virtual environment
- Provide path to cfn-lint executable within virtual environment
- Handle environment setup errors gracefully

### Local Test Integration

**Purpose**: Integrates with existing pytest infrastructure for local development testing.

**Interface**:
```python
# pytest test function
def test_cloudformation_templates_validation():
    # Test implementation
```

**Responsibilities**:
- Execute template validation within pytest framework
- Report results consistent with other test outputs
- Fail tests when validation errors occur
- Provide actionable error messages for developers

### Build Pipeline Integration

**Purpose**: Integrates with buildspec.yml for CI/CD pipeline execution.

**Interface**:
- Python script executable from buildspec commands
- Exit codes for build success/failure
- Structured output for build logs

**Responsibilities**:
- Execute validation during build phase
- Terminate build on validation failures
- Provide clear success/failure reporting
- Handle build environment dependencies

## Data Models

### Template File Model
```python
@dataclass
class TemplateFile:
    path: Path
    relative_path: str
    size: int
    last_modified: datetime
```

### Validation Error Model
```python
@dataclass
class ValidationError:
    rule_id: str
    message: str
    line_number: Optional[int]
    column_number: Optional[int]
    severity: str  # 'error' or 'warning'
```

### Validation Result Model
```python
@dataclass
class ValidationResult:
    template_path: Path
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]
    execution_time: float
```

### Validation Summary Model
```python
@dataclass
class ValidationSummary:
    total_templates: int
    valid_templates: int
    failed_templates: int
    total_errors: int
    total_warnings: int
    results: List[ValidationResult]
    execution_time: float
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Complete Template Discovery
*For any* directory structure under templates/v2 containing CloudFormation template files, the Template_Discovery_System should find all template files recursively regardless of subdirectory depth
**Validates: Requirements 1.1**

### Property 2: Validation Execution Consistency  
*For any* discovered CloudFormation template, the CFN_Linter should execute validation and return a consistent result structure containing validation status and any errors
**Validates: Requirements 1.2**

### Property 3: Error Detail Completeness
*For any* template that fails validation, the system should report error details that include the template file path and specific violation descriptions
**Validates: Requirements 1.3**

### Property 4: Success Status Reporting
*For any* validation run where all templates pass, the system should report successful validation status with appropriate summary information
**Validates: Requirements 1.4**

### Property 5: Graceful Error Handling
*For any* file access error during validation, the system should handle the error gracefully and continue processing remaining templates without terminating
**Validates: Requirements 1.5**

### Property 6: Pytest Integration Consistency
*For any* execution within the pytest framework, the validation system should follow pytest conventions for test discovery, execution, and result reporting
**Validates: Requirements 2.1**

### Property 7: Cross-Environment Logic Consistency
*For any* template validation, the results should be identical whether executed in local development or build pipeline environments
**Validates: Requirements 2.2**

### Property 8: Test Output Format Consistency
*For any* local validation execution, the output format should be consistent with other pytest test outputs in terms of structure and verbosity
**Validates: Requirements 2.3**

### Property 9: Actionable Error Messages
*For any* validation error in local execution, the error message should contain specific file paths and violation details sufficient for developers to fix the issues
**Validates: Requirements 2.4**

### Property 10: Virtual Environment Usage
*For any* execution context (local or build), the system should use the .venv virtual environment for cfn-lint dependency isolation
**Validates: Requirements 2.5, 3.5**

### Property 11: Build Failure Exit Codes
*For any* build pipeline execution with validation failures, the system should return non-zero exit codes to properly fail the build
**Validates: Requirements 3.2**

### Property 12: Build Success Exit Codes
*For any* build pipeline execution with successful validation, the system should return zero exit codes to allow build continuation
**Validates: Requirements 3.3**

### Property 13: Environment Dependency Handling
*For any* execution environment, the system should correctly handle environment-specific Python and dependency configurations
**Validates: Requirements 3.4**

### Property 14: Validation Summary Completeness
*For any* validation execution, the summary report should include total templates processed, validation results, and error counts
**Validates: Requirements 4.1**

### Property 15: Error Aggregation Completeness
*For any* validation run with multiple template errors, all error information should be aggregated and presented in a readable format
**Validates: Requirements 4.2**

### Property 16: File Path Inclusion
*For any* validation result, the output should include the template file path for easy identification and debugging
**Validates: Requirements 4.3**

### Property 17: Empty Directory Handling
*For any* validation execution on a directory with no templates, the system should report this condition clearly rather than silently succeeding
**Validates: Requirements 4.4**

## Error Handling

The system implements comprehensive error handling across multiple layers:

### File System Errors
- **Template Discovery Errors**: Handle permission denied, file not found, and directory access issues
- **Template Reading Errors**: Gracefully handle corrupted files, encoding issues, and large file problems
- **Recovery Strategy**: Continue processing remaining templates when individual files fail

### Validation Errors
- **CFN-Lint Execution Errors**: Handle cfn-lint installation issues, execution failures, and timeout scenarios
- **Template Syntax Errors**: Capture and report YAML/JSON parsing errors before cfn-lint validation
- **Recovery Strategy**: Report validation failures without terminating the entire process

### Environment Errors
- **Virtual Environment Errors**: Handle .venv creation failures, dependency installation issues, and path resolution problems
- **Python Environment Errors**: Handle missing Python installations, version compatibility issues, and module import failures
- **Recovery Strategy**: Provide clear error messages with remediation steps

### Integration Errors
- **Pytest Integration Errors**: Handle test discovery failures, assertion errors, and result reporting issues
- **Build Pipeline Errors**: Handle buildspec execution failures, environment variable issues, and artifact generation problems
- **Recovery Strategy**: Fail fast with appropriate exit codes and detailed error messages

## Testing Strategy

The testing approach combines unit testing and property-based testing to ensure comprehensive validation coverage:

### Unit Testing Approach
Unit tests will verify specific scenarios and edge cases:
- Template discovery with known directory structures
- Validation of specific template files with known errors
- Error handling for specific failure conditions
- Integration points with pytest and buildspec
- Virtual environment setup and dependency management

### Property-Based Testing Approach
Property-based tests will verify universal behaviors across all inputs using **Hypothesis** as the testing library:
- Template discovery properties across randomly generated directory structures
- Validation consistency properties across various template formats
- Error handling properties with randomly generated failure scenarios
- Cross-environment consistency properties with different execution contexts
- Summary reporting properties with various validation result combinations

**Property-Based Testing Configuration**:
- Minimum 100 iterations per property test to ensure thorough coverage
- Each property test tagged with format: **Feature: cfn-template-linter, Property {number}: {property_text}**
- Properties implemented as individual test functions for clear failure isolation
- Smart generators that create realistic CloudFormation template structures and directory layouts

### Testing Integration Requirements
- Both unit and property-based tests execute within the existing pytest framework
- Tests use the same .venv virtual environment as the production code
- Test results integrate with existing JUnit XML reporting for build pipeline compatibility
- Property-based tests complement unit tests by verifying general correctness across many inputs
- Unit tests catch specific bugs while property tests verify universal properties hold across all scenarios