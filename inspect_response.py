#!/usr/bin/env python3
import asyncio
import websockets
import json
import uuid

async def inspect_response():
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
            for i in range(30):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    
                    if data['type'] == 'update':
                        print("\n[RAW UPDATE MESSAGE]")
                        print(json.dumps(data, indent=2))
                        
                        payload = data.get('payload', {})
                        print(f"\n[PAYLOAD ANALYSIS]")
                        print(f"Keys in payload: {list(payload.keys())}")
                        
                        # Check both versions
                        camel_case = payload.get('htmlOutput', '')
                        snake_case = payload.get('html_output', '')
                        
                        print(f"htmlOutput (camelCase): {len(camel_case)} chars")
                        print(f"html_output (snake_case): {len(snake_case)} chars")
                        
                        print(f"htmlOutput == html_output: {camel_case == snake_case}")
                        print(f"htmlOutput is empty: {camel_case == ''}")
                        print(f"html_output is empty: {snake_case == ''}")
                        
                        if camel_case and len(camel_case) < 200:
                            print(f"htmlOutput content: '{camel_case}'")
                        if snake_case and len(snake_case) < 200:
                            print(f"html_output content: '{snake_case}'")
                        
                        return True
                        
                except asyncio.TimeoutError:
                    continue
            
            return False
            
    except Exception as e:
        print(f"[FAIL] {e}")
        return False

if __name__ == "__main__":
    asyncio.run(inspect_response())