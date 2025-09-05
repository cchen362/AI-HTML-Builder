#!/usr/bin/env python3
"""
Simple WebSocket test client to verify content generation is working
"""

import asyncio
import websockets
import json
import uuid

async def test_websocket():
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    print(f"Testing WebSocket connection to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] WebSocket connected successfully")
            
            # Wait for initial sync message
            try:
                sync_msg = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                sync_data = json.loads(sync_msg)
                print(f"✅ Received sync message: {sync_data['type']}")
            except asyncio.TimeoutError:
                print("⚠️ No sync message received (this may be normal)")
            
            # Send a test message
            test_message = {
                "type": "chat",
                "content": "Create a simple webpage with a blue header saying 'Hello World'",
                "attachments": []
            }
            
            print(f"📤 Sending test message: {test_message['content']}")
            await websocket.send(json.dumps(test_message))
            
            # Listen for responses
            responses = []
            timeout_counter = 0
            max_timeout = 30  # 30 second timeout
            
            while timeout_counter < max_timeout:
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    responses.append(data)
                    
                    print(f"📥 Received: {data['type']}")
                    
                    if data['type'] == 'update':
                        print("🎉 Content generation successful!")
                        payload = data.get('payload', {})
                        html_length = len(payload.get('htmlOutput', ''))
                        conv_length = len(payload.get('conversation', ''))
                        print(f"   HTML length: {html_length} chars")
                        print(f"   Conversation length: {conv_length} chars")
                        
                        if html_length > 0:
                            print("✅ HTML content generated successfully!")
                        else:
                            print("❌ No HTML content in response")
                        
                        break
                    elif data['type'] == 'error':
                        print(f"❌ Error received: {data.get('payload', {}).get('error', 'Unknown error')}")
                        break
                    elif data['type'] == 'status':
                        print(f"📊 Status: {data.get('payload', {}).get('message', 'Unknown status')}")
                        
                except asyncio.TimeoutError:
                    timeout_counter += 1
                    if timeout_counter % 5 == 0:  # Print every 5 seconds
                        print(f"⏳ Waiting for response... ({timeout_counter}s)")
            
            if timeout_counter >= max_timeout:
                print("❌ Test timed out - no response received")
                
            print(f"\n📋 Summary: Received {len(responses)} messages")
            return len(responses) > 0 and any(r['type'] == 'update' for r in responses)
            
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_websocket())
    exit(0 if success else 1)