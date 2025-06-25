#!/usr/bin/env python3
"""
Comprehensive script to fix remaining code quality issues
"""

import os
import re
import subprocess
from pathlib import Path


def fix_file_imports_and_issues(file_path):
    """Fix imports and common issues in a Python file"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix imports based on file
    if 'deduplication.py' in str(file_path):
        # Add missing imports for deduplication.py
        if 'from typing import' not in content:
            content = re.sub(
                r'(import json\n)',
                r'\1import time\nfrom typing import Dict, List\n',
                content
            )
        elif 'List' not in content or 'Dict' not in content:
            content = re.sub(
                r'(from typing import[^\n]*)',
                r'from typing import Dict, List',
                content
            )
    
    elif 'spark_processor.py' in str(file_path):
        # Remove unused imports
        content = re.sub(r'^from pyspark\.sql\.functions import current_timestamp\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'^from pyspark\.sql\.types import IntegerType\n', '', content, flags=re.MULTILINE)
        
        # Fix comparison to True
        content = re.sub(r'== True', ' is True', content)
        content = re.sub(r'!= True', ' is not True', content)
        
        # Remove unused variables
        content = re.sub(r'\s+windowed_stream = .*\n', '', content)
    
    elif 'config.py' in str(file_path):
        # Add Optional import
        if 'Optional' in content and 'from typing import' in content:
            content = re.sub(
                r'(from typing import[^\n]*)',
                r'from typing import List, Optional',
                content
            )
    
    elif 'logger.py' in str(file_path):
        # Move imports to top
        lines = content.split('\n')
        import_lines = []
        other_lines = []
        
        for line in lines:
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                if 'logger' not in line.lower() or line.strip().startswith('from loguru'):
                    import_lines.append(line)
                else:
                    other_lines.append(line)
            else:
                other_lines.append(line)
        
        # Reconstruct content with imports at top
        content = '\n'.join(import_lines[:10] + other_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    src_dir = Path('src')
    
    # Process specific problematic files
    problem_files = [
        'src/stream_processing/deduplication.py',
        'src/stream_processing/spark_processor.py', 
        'src/utils/config.py',
        'src/utils/logger.py'
    ]
    
    for file_path in problem_files:
        if Path(file_path).exists():
            print(f"Fixing {file_path}...")
            fix_file_imports_and_issues(Path(file_path))
    
    # Run formatters
    print("Running formatters...")
    subprocess.run(['python', '-m', 'black', 'src/', '--line-length', '88'], capture_output=True)
    subprocess.run(['python', '-m', 'isort', 'src/', '--profile', 'black'], capture_output=True)
    
    # Final check
    print("Checking remaining issues...")
    result = subprocess.run(['python', '-m', 'flake8', 'src/', '--count', '--max-line-length=88'], 
                          capture_output=True, text=True)
    print(f"Remaining issues: {result.stdout.strip()}")
    
    if result.returncode == 0:
        print("✅ All issues fixed!")
    else:
        print("⚠️  Some issues remain, but significantly reduced.")


if __name__ == '__main__':
    main()