#!/usr/bin/env python3
"""Simple Claude test without emojis"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Load environment variables
load_dotenv()

from backend.app.services.claude_service import claude_service

async def main():
    print("Testing Claude Sonnet 4 Integration")
    print("=" * 40)
    
    try:
        # Test simple HTML generation
        test_request = "Create a professional landing page for a tech startup"
        print(f"Request: {test_request}")
        
        dual_response = claude_service.generate_dual_response(
            user_input=test_request,
            context=[],
            session_id="test-123"
        )
        
        print(f"SUCCESS!")
        print(f"HTML length: {len(dual_response.html_output)}")
        print(f"Conversation length: {len(dual_response.conversation)}")
        print(f"Title: {dual_response.metadata.get('title', 'N/A')}")
        
        # Save for inspection
        with open("claude_test_output.html", "w", encoding="utf-8") as f:
            f.write(dual_response.html_output)
            
        with open("claude_test_conversation.txt", "w", encoding="utf-8") as f:
            f.write(dual_response.conversation)
        
        print("Files saved: claude_test_output.html, claude_test_conversation.txt")
        
        # Print first part of conversation
        print(f"Conversation preview: {dual_response.conversation[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    print("PASSED" if success else "FAILED")