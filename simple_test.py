#!/usr/bin/env python3
import asyncio
import websockets
import json
import uuid

async def simple_test():
    session_id = str(uuid.uuid4())
    uri = f"ws://localhost:8000/ws/{session_id}"
    
    print(f"Testing: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("[OK] Connected")
            
            # Send test message
            msg = {
                "type": "chat",
                "content": "Create a simple hello world webpage",
                "attachments": []
            }
            
            print(f"[SEND] {msg['content']}")
            await websocket.send(json.dumps(msg))
            
            # Wait for response
            for i in range(30):  # 30 second timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    print(f"[RECV] {data['type']}")
                    
                    if data['type'] == 'update':
                        html_len = len(data.get('payload', {}).get('htmlOutput', ''))
                        print(f"[SUCCESS] HTML generated: {html_len} chars")
                        return True
                    elif data['type'] == 'error':
                        print(f"[ERROR] {data.get('payload', {}).get('error')}")
                        return False
                        
                except asyncio.TimeoutError:
                    continue
            
            print("[TIMEOUT] No response")
            return False
            
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(simple_test())
    print(f"[RESULT] {'PASS' if success else 'FAIL'}")