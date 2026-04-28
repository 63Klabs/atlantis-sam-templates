"""
Template Discovery Engine for CFN Template Linter.
Recursively discovers CloudFormation template files in the templates/v2 directory structure.
"""

from pathlib import Path
from typing import List, Set
import os


class TemplateDiscovery:
    """Discovers CloudFormation template files in the repository."""
    
    # CloudFormation template file extensions
    TEMPLATE_EXTENSIONS = {'.yml', '.yaml'}
    
    # Files to exclude from template discovery
    EXCLUDED_FILES = {
        'README.md',
        'readme.md',
        'README.yml',
        'readme.yml',
        'README.yaml',
        'readme.yaml',
        '.gitignore',
        '.gitkeep'
    }
    
    # Directories to exclude from template discovery
    EXCLUDED_DIRS = {
        'modules'
    }
    
    def __init__(self, project_root: Path = None):
        """Initialize the template discovery engine.
        
        Args:
            project_root: Path to project root. If None, uses current working directory.
        """
        self.project_root = project_root or Path.cwd()
        self.templates_base_path = self.project_root / "templates" / "v2"
    
    def find_templates(self, base_path: Path = None) -> List[Path]:
        """Find all CloudFormation template files recursively.
        
        Args:
            base_path: Base path to search from. If None, uses templates/v2.
            
        Returns:
            List of Path objects pointing to CloudFormation template files.
        """
        search_path = base_path or self.templates_base_path
        
        if not search_path.exists():
            return []
        
        template_files = []
        
        try:
            # Recursively walk through all directories
            for root, dirs, files in os.walk(search_path):
                root_path = Path(root)
                
                # Skip excluded directories
                dirs[:] = [d for d in dirs if d not in self.EXCLUDED_DIRS]
                
                for file in files:
                    file_path = root_path / file
                    
                    if self.is_cloudformation_template(file_path):
                        template_files.append(file_path)
            
            # Sort for consistent ordering
            template_files.sort()
            
        except (PermissionError, OSError) as e:
            # Handle file system access errors gracefully
            # Log the error but continue processing
            print(f"Warning: Could not access directory {search_path}: {e}")
        
        return template_files
    
    def is_cloudformation_template(self, file_path: Path) -> bool:
        """Determine if a file is a CloudFormation template.
        
        Args:
            file_path: Path to the file to check.
            
        Returns:
            True if the file is a CloudFormation template, False otherwise.
        """
        # Check if file exists and is a regular file
        if not file_path.is_file():
            return False
        
        # Check file extension
        if file_path.suffix.lower() not in self.TEMPLATE_EXTENSIONS:
            return False
        
        # Check if file is in excluded list
        if file_path.name in self.EXCLUDED_FILES:
            return False
        
        # Additional heuristic: check if filename suggests it's a template
        # CloudFormation templates often have "template" in the name
        filename_lower = file_path.name.lower()
        
        # If it has template in the name, it's likely a CloudFormation template
        if 'template' in filename_lower:
            return True
        
        # If it's a .yml/.yaml file in the templates directory structure, 
        # and not excluded, assume it's a CloudFormation template
        try:
            # Check if the file is under the templates/v2 directory
            relative_path = file_path.relative_to(self.project_root)
            path_parts = relative_path.parts
            
            if len(path_parts) >= 2 and path_parts[0] == 'templates' and path_parts[1] == 'v2':
                return True
                
        except ValueError:
            # File is not under project root, could still be a template
            pass
        
        # For files outside the standard structure, we'll be conservative
        # and only include files with "template" in the name
        return 'template' in filename_lower
    
    def get_template_count(self, base_path: Path = None) -> int:
        """Get the count of CloudFormation templates.
        
        Args:
            base_path: Base path to search from. If None, uses templates/v2.
            
        Returns:
            Number of CloudFormation template files found.
        """
        return len(self.find_templates(base_path))
    
    def get_templates_by_category(self, base_path: Path = None) -> dict:
        """Get templates organized by category (subdirectory).
        
        Args:
            base_path: Base path to search from. If None, uses templates/v2.
            
        Returns:
            Dictionary mapping category names to lists of template paths.
        """
        search_path = base_path or self.templates_base_path
        templates = self.find_templates(base_path)
        
        categories = {}
        
        for template_path in templates:
            try:
                # Get relative path from search base
                relative_path = template_path.relative_to(search_path)
                
                # First directory is the category
                if len(relative_path.parts) > 1:
                    category = relative_path.parts[0]
                else:
                    category = "root"
                
                if category not in categories:
                    categories[category] = []
                
                categories[category].append(template_path)
                
            except ValueError:
                # Template is not under search path, put in "other" category
                if "other" not in categories:
                    categories["other"] = []
                categories["other"].append(template_path)
        
        return categories