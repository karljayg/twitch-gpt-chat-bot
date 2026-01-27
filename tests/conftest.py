"""
pytest configuration file to set up Python path for all tests

This ensures all test files can import from project root without individual sys.path manipulation.
"""
import sys
import os

# Add project root to Python path - MUST happen at module import time
# This file is imported by pytest before test collection
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
tests_dir = os.path.abspath(os.path.dirname(__file__))

# Clean up sys.path - remove duplicates and test directories
paths_to_remove = []
for path in sys.path[:]:  # Make a copy to iterate
    if path == tests_dir or 'tests' in path.split(os.sep)[-1]:
        paths_to_remove.append(path)
    elif path == project_root:
        paths_to_remove.append(path)

for path in paths_to_remove:
    while path in sys.path:
        sys.path.remove(path)

# Insert project root at the very beginning
sys.path.insert(0, project_root)
