#!/usr/bin/env python3
"""Debug WebSocket test to see what the backend is actually sending"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime

async def test_websocket_debug():
    """Test WebSocket connection and capture all responses"""
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    print(f"Testing WebSocket connection to: {uri}")
    print(f"Session ID: {session_id}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket connected successfully")
            
            # Wait for initial sync message
            try:
                sync_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                sync_data = json.loads(sync_response)
                print(f"Received sync message: {sync_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                print("No sync message received (timeout)")
            
            # Send a test message
            test_message = {
                "type": "chat",
                "content": "Create a simple landing page with a header and hero section",
                "attachments": []
            }
            
            print(f"Sending test message: {test_message['content']}")
            await websocket.send(json.dumps(test_message))
            
            # Listen for responses
            response_count = 0
            max_responses = 10
            
            while response_count < max_responses:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    response_count += 1
                    
                    print(f"\n--- Response {response_count} ---")
                    print(f"Type: {data.get('type', 'unknown')}")
                    print(f"Full response: {json.dumps(data, indent=2)}")
                    
                    if data.get('type') == 'update':
                        payload = data.get('payload', {})
                        html_output = payload.get('htmlOutput') or payload.get('html_output', '')
                        conversation = payload.get('conversation', '')
                        
                        print(f"HTML Length: {len(html_output)}")
                        print(f"Conversation Length: {len(conversation)}")
                        
                        if html_output:
                            print("HTML content found!")
                            # Save the HTML to a file for inspection
                            with open("debug_output.html", "w", encoding="utf-8") as f:
                                f.write(html_output)
                            print("HTML saved to debug_output.html")
                        else:
                            print("No HTML content in update response!")
                        
                        # Stop after receiving update
                        break
                    
                    elif data.get('type') == 'dual_response':
                        payload = data.get('payload', {})
                        html_output = payload.get('htmlOutput', '')
                        conversation = payload.get('conversation', '')
                        
                        print(f"HTML Length: {len(html_output)}")
                        print(f"Conversation Length: {len(conversation)}")
                        
                        if html_output:
                            print("HTML content found in dual_response!")
                            with open("debug_output.html", "w", encoding="utf-8") as f:
                                f.write(html_output)
                            print("HTML saved to debug_output.html")
                        else:
                            print("No HTML content in dual_response!")
                        
                        break
                        
                    elif data.get('type') == 'error':
                        print(f"ERROR: {data.get('payload', {}).get('error', 'Unknown error')}")
                        break
                    
                    elif data.get('type') == 'status':
                        payload = data.get('payload', {})
                        progress = payload.get('progress', 0)
                        if progress >= 100:
                            print("Processing completed")
                            # Don't break here, wait for actual content
                    
                except asyncio.TimeoutError:
                    print("Timeout waiting for response")
                    break
                except json.JSONDecodeError as e:
                    print(f"JSON decode error: {e}")
                    print(f"Raw response: {response}")
                    break
                except Exception as e:
                    print(f"Unexpected error: {e}")
                    break
            
            print(f"\nTest completed. Received {response_count} responses.")
            
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_debug())