#!/usr/bin/env python3
"""Simple WebSocket test to debug the HTML rendering issue"""

import asyncio
import websockets
import json
import uuid
from datetime import datetime

async def test_websocket_connection():
    """Test WebSocket connection and message exchange"""
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    print(f"Testing WebSocket connection to: {uri}")
    print(f"Session ID: {session_id}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✓ WebSocket connected successfully")
            
            # Wait for initial sync message
            try:
                sync_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                sync_data = json.loads(sync_response)
                print(f"✓ Received sync message: {sync_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                print("⚠ No sync message received (timeout)")
            
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
            max_responses = 10  # Prevent infinite loop
            
            while response_count < max_responses:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                    data = json.loads(response)
                    response_count += 1
                    
                    print(f"\n--- Response {response_count} ---")
                    print(f"Type: {data.get('type', 'unknown')}")
                    
                    if data.get('type') == 'thinking':
                        print(f"Status: {data.get('payload', {}).get('message', 'No message')}")
                    
                    elif data.get('type') == 'dual_response':
                        payload = data.get('payload', {})
                        html_output = payload.get('htmlOutput', '')
                        conversation = payload.get('conversation', '')
                        
                        print(f"HTML Length: {len(html_output)}")
                        print(f"Conversation Length: {len(conversation)}")
                        
                        if html_output:
                            print(f"HTML Preview: {html_output[:200]}...")
                            print("✓ HTML content received!")
                        else:
                            print("❌ No HTML content in response!")
                        
                        if conversation:
                            print(f"Conversation: {conversation[:200]}...")
                        
                        # Stop after receiving dual_response
                        break
                    
                    elif data.get('type') == 'error':
                        print(f"❌ Error: {data.get('payload', {}).get('error', 'Unknown error')}")
                        break
                    
                    elif data.get('type') == 'status':
                        payload = data.get('payload', {})
                        print(f"Status: {payload.get('message', 'No message')} ({payload.get('progress', 0)}%)")
                        if payload.get('progress', 0) >= 100:
                            print("✓ Processing completed")
                            break
                    
                except asyncio.TimeoutError:
                    print("⚠ Timeout waiting for response")
                    break
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                    print(f"Raw response: {response}")
                    break
                except Exception as e:
                    print(f"❌ Unexpected error: {e}")
                    break
            
            print(f"\nTest completed. Received {response_count} responses.")
            
    except websockets.exceptions.ConnectionClosed as e:
        print(f"❌ WebSocket connection closed: {e}")
    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_connection())