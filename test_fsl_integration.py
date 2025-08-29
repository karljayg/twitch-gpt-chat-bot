#!/usr/bin/env python3
"""
Test script for FSL integration
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.fsl_integration import FSLIntegration
from settings import config

def test_fsl_integration():
    """Test the FSL integration functionality"""
    
    print("Testing FSL Integration...")
    
    # Initialize FSL integration
    fsl = FSLIntegration(
        api_url=config.FSL_API_URL,
        api_token=config.FSL_API_TOKEN,
        reviewer_weight=config.FSL_REVIEWER_WEIGHT
    )
    
    # Test reviewer creation
    test_username = "test_user_123"
    print(f"\n1. Testing reviewer creation for: {test_username}")
    
    result = fsl.create_reviewer(test_username)
    if result:
        print(f"✅ Successfully created reviewer: {result}")
    else:
        print("❌ Failed to create reviewer")
    
    # Test checking if reviewer exists
    print(f"\n2. Testing reviewer existence check for: {test_username}")
    
    exists = fsl.check_reviewer_exists(test_username)
    print(f"✅ Reviewer exists: {exists}")
    
    # Test getting reviewer link
    print(f"\n3. Testing getting reviewer link for: {test_username}")
    
    link = fsl.get_reviewer_link(test_username)
    if link:
        print(f"✅ Got reviewer link: {link}")
    else:
        print("❌ Failed to get reviewer link")
    
    # Test with non-existent user
    print(f"\n4. Testing with non-existent user: nonexistent_user")
    
    exists = fsl.check_reviewer_exists("nonexistent_user")
    print(f"✅ Non-existent user check: {exists} (should be False)")
    
    print("\n🎉 FSL Integration test completed!")

if __name__ == "__main__":
    test_fsl_integration() 