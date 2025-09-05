#!/usr/bin/env python3
"""Debug Claude raw response"""

import os
import sys
import asyncio
from dotenv import load_dotenv
import anthropic

# Load environment variables
load_dotenv()

async def test_claude_raw():
    """Test Claude API directly to see raw response format"""
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("No API key!")
        return
    
    client = anthropic.Anthropic(api_key=api_key)
    
    system_prompt = """You are an exceptional UI/UX designer who creates professional single-file HTML documents.

Create a complete HTML file with inline CSS. Return your response as:

**HTML:**
[Complete HTML document starting with <!DOCTYPE html>]

**CONVERSATION:**
[Brief explanation of your design decisions]"""

    try:
        print("Calling Claude API...")
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.7,
            messages=[
                {"role": "user", "content": system_prompt},
                {"role": "user", "content": "Create a professional landing page for a tech startup"}
            ]
        )
        
        raw_response = response.content[0].text
        print(f"Response length: {len(raw_response)}")
        print("=" * 50)
        print("FIRST 500 CHARS:")
        print(raw_response[:500])
        print("=" * 50)
        print("LAST 500 CHARS:")
        print(raw_response[-500:])
        
        # Save full response
        with open("claude_raw_response.txt", "w", encoding="utf-8") as f:
            f.write(raw_response)
        print("\nFull response saved to claude_raw_response.txt")
        
        # Test our parsing
        import re
        html_match = re.search(r'\*\*HTML:\*\*\s*\n(.*?)(?=\n\s*\*\*CONVERSATION:\*\*|$)', raw_response, re.DOTALL | re.IGNORECASE)
        conv_match = re.search(r'\*\*CONVERSATION:\*\*\s*\n(.*?)$', raw_response, re.DOTALL | re.IGNORECASE)
        
        print(f"\nHTML match found: {html_match is not None}")
        print(f"Conversation match found: {conv_match is not None}")
        
        if html_match:
            html_content = html_match.group(1).strip()
            print(f"HTML content length: {len(html_content)}")
            print(f"HTML starts with DOCTYPE: {html_content.startswith('<!DOCTYPE html>')}")
        
        if conv_match:
            conv_content = conv_match.group(1).strip()
            print(f"Conversation content: {conv_content[:100]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_claude_raw())