#!/usr/bin/env python3
"""
Test script to replicate the content disappearing issue during reiteration.

This script will:
1. Connect to the WebSocket API
2. Generate initial comprehensive HTML content
3. Request a modification that triggers surgical editing
4. Compare before/after HTML content to confirm the issue
"""

import asyncio
import websockets
import json
import uuid
import sys
from datetime import datetime

class ContentDisappearingTest:
    def __init__(self):
        self.websocket_url = "ws://localhost:8000/ws/"
        self.session_id = str(uuid.uuid4())
        self.websocket = None
        self.initial_html = None
        self.modified_html = None
        self.test_results = {}

    async def connect(self):
        """Connect to WebSocket"""
        try:
            self.websocket = await websockets.connect(f"{self.websocket_url}{self.session_id}")
            print(f"Connected to WebSocket with session ID: {self.session_id}")
            return True
        except Exception as e:
            print(f"Failed to connect to WebSocket: {e}")
            return False

    async def send_message(self, content, message_type="chat"):
        """Send a message and wait for response"""
        message = {
            "type": message_type,
            "content": content,
            "colorScheme": "light",
            "attachments": []
        }
        
        print(f"\nSending message: {content[:50]}...")
        await self.websocket.send(json.dumps(message))
        
        responses = []
        while True:
            try:
                # Wait for response with timeout
                response = await asyncio.wait_for(self.websocket.recv(), timeout=30.0)
                data = json.loads(response)
                responses.append(data)
                
                print(f"Received: {data.get('type', 'unknown')}")
                
                # Check if this is a dual_response with HTML
                if data.get("type") == "dual_response":
                    html_output = data.get("payload", {}).get("htmlOutput")
                    conversation = data.get("payload", {}).get("conversation", "")
                    
                    if html_output:
                        print(f"HTML length: {len(html_output)}")
                        print(f"Conversation: {conversation[:100]}...")
                        return html_output, conversation
                
                # Check for status completion
                elif data.get("type") == "status":
                    status_msg = data.get("payload", {}).get("message", "")
                    if "Ready for your next request" in status_msg:
                        break
                        
                # Check for errors
                elif data.get("type") == "error":
                    error_msg = data.get("payload", {}).get("error", "Unknown error")
                    print(f"Error received: {error_msg}")
                    return None, error_msg
                    
            except asyncio.TimeoutError:
                print("Timeout waiting for response")
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
        
        return None, "No HTML content received"

    async def test_initial_generation(self):
        """Generate initial comprehensive HTML content"""
        print("\n=== STEP 1: Generate Initial Content ===")
        
        # Request comprehensive content similar to the screenshot
        initial_request = """Create a comprehensive impact assessment report titled "Impact Assessment Report - Time Sensitive Case Management Solutions" with the following sections:

1. Problem Statement with detailed analysis
2. Technical Solutions with multiple options and comparisons
3. Risk Analysis with identified issues and mitigation strategies
4. Recommendations with implementation timeline

Include tabbed navigation, professional styling with blue colors, and make it comprehensive with multiple paragraphs per section."""

        html_content, conversation = await self.send_message(initial_request)
        
        if html_content:
            self.initial_html = html_content
            print(f"SUCCESS: Generated initial HTML ({len(html_content)} characters)")
            print(f"Conversation: {conversation}")
            
            # Save to file for inspection
            with open("test_initial_content.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("Saved initial content to test_initial_content.html")
            
            return True
        else:
            print(f"FAILED: {conversation}")
            return False

    async def test_modification_request(self):
        """Request modification that should trigger surgical editing"""
        print("\n=== STEP 2: Request Modification (Should Trigger Surgical Editing) ===")
        
        # Use modification trigger words that should activate surgical editing
        modification_request = "Remove the Option Comparison tab and keep the rest of the content and formatting"
        
        html_content, conversation = await self.send_message(modification_request)
        
        if html_content:
            self.modified_html = html_content
            print(f"SUCCESS: Generated modified HTML ({len(html_content)} characters)")
            print(f"Conversation: {conversation}")
            
            # Save to file for inspection
            with open("test_modified_content.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("Saved modified content to test_modified_content.html")
            
            return True
        else:
            print(f"FAILED: {conversation}")
            return False

    def analyze_content_difference(self):
        """Compare initial vs modified HTML to detect content disappearing"""
        print("\n=== STEP 3: Analyze Content Difference ===")
        
        if not self.initial_html or not self.modified_html:
            print("ERROR: Missing HTML content for comparison")
            return False
        
        # Basic metrics
        initial_length = len(self.initial_html)
        modified_length = len(self.modified_html)
        length_ratio = modified_length / initial_length if initial_length > 0 else 0
        
        print(f"Initial HTML length: {initial_length}")
        print(f"Modified HTML length: {modified_length}")
        print(f"Length ratio: {length_ratio:.3f}")
        
        # Check for title extraction
        import re
        initial_title = self.extract_title(self.initial_html)
        modified_title = self.extract_title(self.modified_html)
        
        print(f"Initial title: {initial_title}")
        print(f"Modified title: {modified_title}")
        
        # Check for body content
        initial_body_content = self.extract_body_content_length(self.initial_html)
        modified_body_content = self.extract_body_content_length(self.modified_html)
        
        print(f"Initial body content length: {initial_body_content}")
        print(f"Modified body content length: {modified_body_content}")
        
        # Determine if content disappeared
        content_disappeared = (
            modified_length < initial_length * 0.3 or  # Less than 30% of original
            modified_body_content < initial_body_content * 0.2  # Less than 20% of body content
        )
        
        self.test_results = {
            "timestamp": datetime.now().isoformat(),
            "initial_length": initial_length,
            "modified_length": modified_length,
            "length_ratio": length_ratio,
            "initial_title": initial_title,
            "modified_title": modified_title,
            "initial_body_content": initial_body_content,
            "modified_body_content": modified_body_content,
            "content_disappeared": content_disappeared
        }
        
        if content_disappeared:
            print("\nISSUE CONFIRMED: Content has significantly disappeared!")
            print("This confirms the hypothesis that surgical editing is truncating content.")
        else:
            print("\nContent appears to be preserved during modification.")
        
        return content_disappeared

    def extract_title(self, html_content):
        """Extract title from HTML"""
        import re
        match = re.search(r'<title>(.*?)</title>', html_content, re.IGNORECASE)
        return match.group(1) if match else "No title found"

    def extract_body_content_length(self, html_content):
        """Extract body content and measure its length"""
        import re
        body_match = re.search(r'<body[^>]*>(.*?)</body>', html_content, re.DOTALL | re.IGNORECASE)
        if body_match:
            body_content = body_match.group(1)
            # Remove script and style tags
            body_content = re.sub(r'<script[^>]*>.*?</script>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
            body_content = re.sub(r'<style[^>]*>.*?</style>', '', body_content, flags=re.DOTALL | re.IGNORECASE)
            return len(body_content.strip())
        return 0

    def save_test_results(self):
        """Save test results to JSON file"""
        with open("test_results.json", "w") as f:
            json.dump(self.test_results, f, indent=2)
        print(f"\nTest results saved to test_results.json")

    async def disconnect(self):
        """Close WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("WebSocket connection closed")

    async def run_full_test(self):
        """Run the complete test suite"""
        print("Starting Content Disappearing Test")
        print("=" * 50)
        
        try:
            # Step 1: Connect
            if not await self.connect():
                return False
            
            # Step 2: Generate initial content
            if not await self.test_initial_generation():
                return False
            
            # Step 3: Request modification
            if not await self.test_modification_request():
                return False
            
            # Step 4: Analyze results
            issue_confirmed = self.analyze_content_difference()
            
            # Step 5: Save results
            self.save_test_results()
            
            return issue_confirmed
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            return False
        finally:
            await self.disconnect()

async def main():
    """Main test runner"""
    test = ContentDisappearingTest()
    issue_found = await test.run_full_test()
    
    print("\n" + "=" * 50)
    if issue_found:
        print("TEST RESULT: ISSUE CONFIRMED - Content disappearing during reiteration")
        print("The surgical editing approach is truncating HTML content as hypothesized.")
    else:
        print("TEST RESULT: No content disappearing issue detected")
        print("The hypothesis may need revision.")
    
    return issue_found

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)