#!/usr/bin/env python3
"""
Simple test to verify dark mode implementation
"""
import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_dark_mode():
    """Simple test for dark mode WebSocket communication"""
    
    session_id = "test-dark-mode-simple"
    ws_url = f"ws://localhost:8000/ws/{session_id}"
    
    print("Testing dark mode implementation...")
    print(f"Connecting to: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("Connected successfully")
            
            # Send test message with dark color scheme
            message = {
                "type": "chat",
                "content": "Create a landing page",
                "colorScheme": "dark",
                "attachments": []
            }
            
            print("Sending message with colorScheme: dark")
            await websocket.send(json.dumps(message))
            
            print("Waiting for response...")
            
            # Wait for response
            async for msg in websocket:
                try:
                    data = json.loads(msg)
                    msg_type = data.get('type', 'unknown')
                    
                    print(f"Received message type: {msg_type}")
                    
                    if msg_type == 'dual_response':
                        html_output = data.get('payload', {}).get('htmlOutput', '')
                        
                        print(f"HTML Length: {len(html_output)} characters")
                        
                        # Check for dark mode CSS
                        has_dark_css = '@media (prefers-color-scheme: dark)' in html_output
                        print(f"Dark mode CSS present: {has_dark_css}")
                        
                        # Check for specific dark colors
                        dark_colors = ['#1a1a1a', '#2d2d2d', '#3a3a3a', '#e0e0e0']
                        found_colors = [color for color in dark_colors if color in html_output]
                        print(f"Dark colors found: {found_colors}")
                        
                        # Save for inspection
                        with open('dark_mode_test_output.html', 'w', encoding='utf-8') as f:
                            f.write(html_output)
                        print("HTML saved to dark_mode_test_output.html")
                        
                        # Success criteria
                        if has_dark_css and found_colors:
                            print("SUCCESS: Dark mode implementation working!")
                            return True
                        else:
                            print("FAILED: Dark mode features missing")
                            return False
                            
                    elif msg_type == 'error':
                        error_msg = data.get('payload', {}).get('error', 'Unknown error')
                        print(f"Error: {error_msg}")
                        return False
                        
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    continue
                except UnicodeError as e:
                    print(f"Unicode error (ignoring): {e}")
                    continue
                    
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def main():
    """Run the simple dark mode test"""
    print("AI HTML Builder - Simple Dark Mode Test")
    print("=" * 50)
    
    success = asyncio.run(test_dark_mode())
    
    if success:
        print("\nTest PASSED: Dark mode implementation is working")
        return 0
    else:
        print("\nTest FAILED: Dark mode implementation needs fixing")
        return 1

if __name__ == "__main__":
    sys.exit(main())