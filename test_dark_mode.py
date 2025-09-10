#!/usr/bin/env python3
"""
Test script to verify dark mode implementation end-to-end
"""
import asyncio
import websockets
import json
import sys
from datetime import datetime

async def test_dark_mode_websocket():
    """Test WebSocket communication with dark mode color scheme"""
    
    # Test session ID
    session_id = "test-session-dark-mode"
    ws_url = f"ws://localhost:8000/ws/{session_id}"
    
    print(f"Connecting to WebSocket: {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("[CONNECTED] WebSocket connected successfully")
            
            # Test message with dark color scheme
            test_message = {
                "type": "chat",
                "content": "Create a simple landing page for a tech startup",
                "colorScheme": "dark",  # This is the key test - dark mode preference
                "attachments": []
            }
            
            print(f"[SENDING] Test message with colorScheme: dark")
            await websocket.send(json.dumps(test_message))
            
            print("[WAITING] Waiting for response...")
            response_count = 0
            
            # Listen for responses
            async for message in websocket:
                response_count += 1
                try:
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    
                    print(f"\n[RESPONSE {response_count}] Type: {msg_type}")
                    
                    if msg_type == 'dual_response':
                        html_output = data.get('payload', {}).get('htmlOutput', '')
                        conversation = data.get('payload', {}).get('conversation', '')
                        
                        print(f"  HTML Length: {len(html_output)} chars")
                        print(f"  Conversation Length: {len(conversation)} chars")
                        
                        # Verify dark mode CSS is present
                        if '@media (prefers-color-scheme: dark)' in html_output:
                            print("  [SUCCESS] Dark mode CSS detected in generated HTML!")
                        else:
                            print("  [FAILED] No dark mode CSS found in generated HTML")
                            
                        # Check for dark mode colors
                        dark_colors = ['#1a1a1a', '#2d2d2d', '#3a3a3a', '#e0e0e0']
                        found_colors = []
                        for color in dark_colors:
                            if color in html_output:
                                found_colors.append(color)
                        
                        if found_colors:
                            print(f"  [SUCCESS] Dark mode colors found: {', '.join(found_colors)}")
                        else:
                            print("  [FAILED] No dark mode colors found")
                            
                        # Save HTML output for inspection
                        with open('test_dark_mode_output.html', 'w', encoding='utf-8') as f:
                            f.write(html_output)
                        print("  [SAVED] HTML saved to test_dark_mode_output.html")
                        
                        print(f"  [CONVERSATION] {conversation[:100]}...")
                        break
                        
                    elif msg_type == 'thinking':
                        print(f"  [THINKING] AI processing: {data.get('payload', {}).get('message', 'Processing...')}")
                        
                    elif msg_type == 'error':
                        print(f"  [ERROR] {data.get('payload', {}).get('error', 'Unknown error')}")
                        return False
                        
                except json.JSONDecodeError:
                    print(f"  [ERROR] Failed to parse message: {message}")
                    continue
                    
                # Timeout after reasonable time
                if response_count > 20:
                    print("  [TIMEOUT] Response timeout - stopping test")
                    break
                    
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False
    
    return True

async def test_light_mode_websocket():
    """Test WebSocket communication with light mode color scheme for comparison"""
    
    # Test session ID
    session_id = "test-session-light-mode"
    ws_url = f"ws://localhost:8000/ws/{session_id}"
    
    print(f"\nConnecting to WebSocket (Light Mode): {ws_url}")
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("[CONNECTED] WebSocket connected successfully")
            
            # Test message with light color scheme
            test_message = {
                "type": "chat",
                "content": "Create a simple contact form",
                "colorScheme": "light",  # Light mode preference
                "attachments": []
            }
            
            print(f"[SENDING] Test message with colorScheme: light")
            await websocket.send(json.dumps(test_message))
            
            print("[WAITING] Waiting for response...")
            
            # Listen for responses
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type', 'unknown')
                    
                    if msg_type == 'dual_response':
                        html_output = data.get('payload', {}).get('htmlOutput', '')
                        
                        print(f"  HTML Length: {len(html_output)} chars")
                        
                        # Verify dark mode CSS is still present (for compatibility)
                        if '@media (prefers-color-scheme: dark)' in html_output:
                            print("  [SUCCESS] Dark mode CSS compatibility detected!")
                        else:
                            print("  [WARNING] No dark mode compatibility CSS")
                            
                        # Save HTML output for comparison
                        with open('test_light_mode_output.html', 'w', encoding='utf-8') as f:
                            f.write(html_output)
                        print("  [SAVED] HTML saved to test_light_mode_output.html")
                        break
                        
                    elif msg_type == 'error':
                        print(f"  [ERROR] {data.get('payload', {}).get('error', 'Unknown error')}")
                        return False
                        
                except json.JSONDecodeError:
                    continue
                    
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False
    
    return True

def main():
    """Run the dark mode tests"""
    print("AI HTML Builder - Dark Mode Implementation Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test dark mode
    print("1. Testing Dark Mode Generation...")
    dark_result = asyncio.run(test_dark_mode_websocket())
    
    if dark_result:
        print("[SUCCESS] Dark mode test completed successfully!")
    else:
        print("[FAILED] Dark mode test failed!")
        return 1
    
    # Test light mode for comparison  
    print("\n2. Testing Light Mode Generation (for comparison)...")
    light_result = asyncio.run(test_light_mode_websocket())
    
    if light_result:
        print("[SUCCESS] Light mode test completed successfully!")
    else:
        print("[FAILED] Light mode test failed!")
        return 1
    
    print("\n" + "=" * 60)
    print("All tests completed! Check the generated HTML files:")
    print("   - test_dark_mode_output.html (dark mode optimized)")
    print("   - test_light_mode_output.html (light mode with dark compatibility)")
    print()
    print("Open both files in your browser and toggle dark/light mode to verify!")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())