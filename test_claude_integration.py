#!/usr/bin/env python3
"""Test Claude Sonnet 4 integration to verify it's working correctly"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Load environment variables
load_dotenv()

from backend.app.services.claude_service import claude_service

async def test_claude_integration():
    """Test Claude integration with a simple request"""
    print("🧪 Testing Claude Sonnet 4 Integration")
    print("=" * 50)
    
    # Test API key presence
    api_key = os.getenv("ANTHROPIC_API_KEY")
    print(f"✅ API Key present: {'Yes' if api_key else 'No'}")
    print(f"✅ API Key format: {'Valid (sk-ant-*)' if api_key and api_key.startswith('sk-ant-') else 'Invalid'}")
    
    if not api_key or not api_key.startswith('sk-ant-'):
        print("❌ ERROR: Invalid or missing Anthropic API key!")
        return False
    
    try:
        print("\n🔗 Testing Claude API connection...")
        connection_test = await claude_service.validate_connection()
        
        if not connection_test:
            print("❌ Connection test failed!")
            return False
        
        print("✅ Claude API connection successful!")
        
        print("\n🎨 Testing HTML generation with simple request...")
        test_request = "Create a professional landing page for a tech startup"
        
        print(f"📝 Request: {test_request}")
        
        dual_response = claude_service.generate_dual_response(
            user_input=test_request,
            context=[],
            session_id="test-session-123"
        )
        
        print(f"\n✅ Generation successful!")
        print(f"📊 HTML length: {len(dual_response.html_output)} characters")
        print(f"💬 Conversation length: {len(dual_response.conversation)} characters")
        print(f"📄 Title: {dual_response.metadata.get('title', 'Unknown')}")
        print(f"🏷️ Type: {dual_response.metadata.get('type', 'Unknown')}")
        
        # Check if HTML is valid
        if dual_response.html_output.startswith('<!DOCTYPE html>'):
            print("✅ Valid HTML structure detected")
        else:
            print("⚠️ HTML may not have proper DOCTYPE")
        
        # Check conversation quality
        if len(dual_response.conversation.strip()) > 20:
            print("✅ Meaningful conversation response generated")
            print(f"💭 Conversation preview: {dual_response.conversation[:100]}...")
        else:
            print("⚠️ Conversation response seems short or missing")
            print(f"💭 Full conversation: '{dual_response.conversation}'")
        
        # Save outputs for inspection
        with open("test_claude_output.html", "w", encoding="utf-8") as f:
            f.write(dual_response.html_output)
        print("✅ HTML saved to test_claude_output.html")
        
        with open("test_claude_conversation.txt", "w", encoding="utf-8") as f:
            f.write(dual_response.conversation)
        print("✅ Conversation saved to test_claude_conversation.txt")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR during testing: {e}")
        print(f"🔍 Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 Starting Claude Sonnet 4 Integration Test")
    
    try:
        success = asyncio.run(test_claude_integration())
        if success:
            print("\n🎉 ✅ All tests passed! Claude integration is working correctly!")
        else:
            print("\n💥 ❌ Tests failed! Check the errors above.")
    except KeyboardInterrupt:
        print("\n⏹️ Test interrupted by user")
    except Exception as e:
        print(f"\n💥 ❌ Unexpected error: {e}")