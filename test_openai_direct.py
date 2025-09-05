#!/usr/bin/env python3
"""Direct test of OpenAI API to verify it's working"""

import os
import asyncio
from dotenv import load_dotenv
import openai

# Load environment variables
load_dotenv()

async def test_openai_api():
    """Test OpenAI API directly"""
    
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"API Key present: {'Yes' if api_key else 'No'}")
    print(f"API Key format: {'Valid (sk-*)' if api_key and api_key.startswith('sk-') else 'Invalid'}")
    print(f"API Key length: {len(api_key) if api_key else 0}")
    
    if not api_key:
        print("ERROR: No OpenAI API key found!")
        return False
    
    if not api_key.startswith('sk-'):
        print("ERROR: Invalid API key format!")
        return False
    
    try:
        print("\nTesting OpenAI API connection...")
        client = openai.AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'API test successful' and create a simple HTML hello world page"}
            ],
            max_tokens=500
        )
        
        result = response.choices[0].message.content
        print("SUCCESS: OpenAI API is working!")
        print(f"Response length: {len(result)}")
        print(f"First 200 chars: {result[:200]}...")
        
        # Save response for inspection
        with open("openai_test_response.txt", "w", encoding="utf-8") as f:
            f.write(result)
        print("Full response saved to openai_test_response.txt")
        
        return True
        
    except openai.AuthenticationError as e:
        print(f"AUTHENTICATION ERROR: {e}")
        print("The API key is invalid or expired!")
        return False
        
    except openai.RateLimitError as e:
        print(f"RATE LIMIT ERROR: {e}")
        print("You've hit the rate limit or quota!")
        return False
        
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openai_api())
    if success:
        print("\n✓ OpenAI API is working correctly!")
    else:
        print("\n✗ OpenAI API test failed!")