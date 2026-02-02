"""
Unit tests for template-parameter-standards.md steering document.
Tests that the steering document exists and contains all required parameter definitions.
"""

import pytest
import os
from pathlib import Path


@pytest.fixture
def steering_doc_path():
    """Get the path to the steering document."""
    return Path(__file__).parent.parent / ".kiro" / "steering" / "template-parameter-standards.md"


@pytest.fixture
def steering_doc_content(steering_doc_path):
    """Load the steering document content."""
    with open(steering_doc_path, 'r') as f:
        return f.read()


class TestSteeringDocumentExists:
    """Test that the steering document file exists."""
    
    def test_file_exists(self, steering_doc_path):
        """Test that template-parameter-standards.md exists."""
        assert steering_doc_path.exists(), f"Steering document not found at {steering_doc_path}"
    
    def test_file_is_not_empty(self, steering_doc_content):
        """Test that the steering document is not empty."""
        assert len(steering_doc_content) > 0, "Steering document is empty"


class TestRequiredParameters:
    """Test that all required parameters are documented."""
    
    REQUIRED_PARAMETERS = [
        'Prefix',
        'ProjectId',
        'StageId',
        'S3LogBucketName',
        'S3BucketNameOrgPrefix',
        'DeployEnvironment'
    ]
    
    @pytest.mark.parametrize("param_name", REQUIRED_PARAMETERS)
    def test_parameter_documented(self, steering_doc_content, param_name):
        """Test that each required parameter is documented."""
        assert f"### {param_name}" in steering_doc_content, \
            f"Parameter '{param_name}' not found in steering document"


class TestParameterFields:
    """Test that each parameter has required fields."""
    
    def test_prefix_has_required_fields(self, steering_doc_content):
        """Test that Prefix parameter has all required fields."""
        # Find the Prefix section
        assert "### Prefix" in steering_doc_content
        prefix_section = self._extract_section(steering_doc_content, "### Prefix", "### ProjectId")
        
        # Check required fields
        assert "**Purpose**:" in prefix_section, "Prefix missing Purpose field"
        assert "**Metadata Group**:" in prefix_section, "Prefix missing Metadata Group field"
        assert "**Definition**:" in prefix_section, "Prefix missing Definition field"
        assert "Type: String" in prefix_section, "Prefix missing Type in definition"
        assert "AllowedPattern:" in prefix_section, "Prefix missing AllowedPattern in definition"
        assert "**Usage Notes**:" in prefix_section, "Prefix missing Usage Notes field"
        assert "**Examples**:" in prefix_section, "Prefix missing Examples field"
    
    def test_projectid_has_required_fields(self, steering_doc_content):
        """Test that ProjectId parameter has all required fields."""
        assert "### ProjectId" in steering_doc_content
        projectid_section = self._extract_section(steering_doc_content, "### ProjectId", "### StageId")
        
        assert "**Purpose**:" in projectid_section
        assert "**Metadata Group**:" in projectid_section
        assert "**Definition**:" in projectid_section
        assert "Type: String" in projectid_section
        assert "AllowedPattern:" in projectid_section
        assert "**Usage Notes**:" in projectid_section
        assert "**Examples**:" in projectid_section
    
    def test_stageid_has_required_fields(self, steering_doc_content):
        """Test that StageId parameter has all required fields."""
        assert "### StageId" in steering_doc_content
        stageid_section = self._extract_section(steering_doc_content, "### StageId", "### S3LogBucketName")
        
        assert "**Purpose**:" in stageid_section
        assert "**Metadata Group**:" in stageid_section
        assert "**Definition**:" in stageid_section
        assert "Type: String" in stageid_section
        assert "AllowedPattern:" in stageid_section
        assert "**Usage Notes**:" in stageid_section
        assert "**Examples**:" in stageid_section
    
    def test_s3logbucketname_has_required_fields(self, steering_doc_content):
        """Test that S3LogBucketName parameter has all required fields."""
        assert "### S3LogBucketName" in steering_doc_content
        s3log_section = self._extract_section(steering_doc_content, "### S3LogBucketName", "### S3BucketNameOrgPrefix")
        
        assert "**Purpose**:" in s3log_section
        assert "**Metadata Group**:" in s3log_section
        assert "**Definition**:" in s3log_section
        assert "Type: String" in s3log_section
        assert "AllowedPattern:" in s3log_section
        assert "**Usage Notes**:" in s3log_section
        assert "**Examples**:" in s3log_section
    
    def test_s3bucketnameorgprefix_has_required_fields(self, steering_doc_content):
        """Test that S3BucketNameOrgPrefix parameter has all required fields."""
        assert "### S3BucketNameOrgPrefix" in steering_doc_content
        s3org_section = self._extract_section(steering_doc_content, "### S3BucketNameOrgPrefix", "### DeployEnvironment")
        
        assert "**Purpose**:" in s3org_section
        assert "**Metadata Group**:" in s3org_section
        assert "**Definition**:" in s3org_section
        assert "Type: String" in s3org_section
        assert "AllowedPattern:" in s3org_section
        assert "**Usage Notes**:" in s3org_section
        assert "**Examples**:" in s3org_section
    
    def test_deployenvironment_has_required_fields(self, steering_doc_content):
        """Test that DeployEnvironment parameter has all required fields."""
        assert "### DeployEnvironment" in steering_doc_content
        deploy_section = self._extract_section(steering_doc_content, "### DeployEnvironment", "## Parameter Groups")
        
        assert "**Purpose**:" in deploy_section
        assert "**Metadata Group**:" in deploy_section
        assert "**Definition**:" in deploy_section
        assert "Type: String" in deploy_section
        assert "AllowedValues:" in deploy_section
        assert "**Usage Notes**:" in deploy_section
        assert "**Examples**:" in deploy_section
    
    @staticmethod
    def _extract_section(content, start_marker, end_marker):
        """Extract a section of content between two markers."""
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)
        if start_idx == -1:
            return ""
        if end_idx == -1:
            return content[start_idx:]
        return content[start_idx:end_idx]


class TestMetadataGroupLabels:
    """Test that metadata group labels are specified."""
    
    REQUIRED_GROUPS = [
        "Application Resource Naming",
        "Deployment Environment",
        "Supporting Resources"
    ]
    
    def test_parameter_groups_section_exists(self, steering_doc_content):
        """Test that Parameter Groups section exists."""
        assert "## Parameter Groups" in steering_doc_content, \
            "Parameter Groups section not found in steering document"
    
    @pytest.mark.parametrize("group_label", REQUIRED_GROUPS)
    def test_metadata_group_documented(self, steering_doc_content, group_label):
        """Test that each required metadata group is documented."""
        # Extract the Parameter Groups section
        groups_section = self._extract_parameter_groups_section(steering_doc_content)
        
        assert f'"{group_label}"' in groups_section or f"**Label**: `\"{group_label}\"`" in groups_section, \
            f"Metadata group '{group_label}' not found in Parameter Groups section"
    
    def test_prefix_metadata_group_specified(self, steering_doc_content):
        """Test that Prefix has Metadata Group specified."""
        prefix_section = self._extract_section(steering_doc_content, "### Prefix", "### ProjectId")
        assert "**Metadata Group**: \"Application Resource Naming\"" in prefix_section, \
            "Prefix missing Metadata Group specification"
    
    def test_s3logbucketname_metadata_group_specified(self, steering_doc_content):
        """Test that S3LogBucketName has Metadata Group specified."""
        s3log_section = self._extract_section(steering_doc_content, "### S3LogBucketName", "### S3BucketNameOrgPrefix")
        assert "**Metadata Group**: \"Supporting Resources\"" in s3log_section, \
            "S3LogBucketName missing Metadata Group specification"
    
    def test_deployenvironment_metadata_group_specified(self, steering_doc_content):
        """Test that DeployEnvironment has Metadata Group specified."""
        deploy_section = self._extract_section(steering_doc_content, "### DeployEnvironment", "## Parameter Groups")
        assert "**Metadata Group**: \"Deployment Environment\"" in deploy_section, \
            "DeployEnvironment missing Metadata Group specification"
    
    @staticmethod
    def _extract_section(content, start_marker, end_marker):
        """Extract a section of content between two markers."""
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker, start_idx)
        if start_idx == -1:
            return ""
        if end_idx == -1:
            return content[start_idx:]
        return content[start_idx:end_idx]
    
    @staticmethod
    def _extract_parameter_groups_section(content):
        """Extract the Parameter Groups section."""
        start_idx = content.find("## Parameter Groups")
        if start_idx == -1:
            return ""
        # Find the next ## heading
        next_section = content.find("\n## ", start_idx + 1)
        if next_section == -1:
            return content[start_idx:]
        return content[start_idx:next_section]


class TestDocumentStructure:
    """Test that the document has the required structure."""
    
    REQUIRED_SECTIONS = [
        "## Overview",
        "## Standard Parameters",
        "## Parameter Groups",
        "## Validation Patterns",
        "## Usage Guidelines",
        "## Examples"
    ]
    
    @pytest.mark.parametrize("section", REQUIRED_SECTIONS)
    def test_section_exists(self, steering_doc_content, section):
        """Test that each required section exists."""
        assert section in steering_doc_content, \
            f"Required section '{section}' not found in steering document"
