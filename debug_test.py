#!/usr/bin/env python3
import asyncio
import websockets
import json
import uuid

async def debug_test():
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
            
            print(f"[SEND] {json.dumps(msg, indent=2)}")
            await websocket.send(json.dumps(msg))
            
            # Wait for response
            responses = []
            for i in range(30):  # 30 second timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    responses.append(data)
                    print(f"[RECV-{i}] Type: {data['type']}")
                    
                    if data['type'] == 'update':
                        payload = data.get('payload', {})
                        html_output = payload.get('htmlOutput', '')
                        html_output_snake = payload.get('html_output', '')
                        conversation = payload.get('conversation', '')
                        
                        print(f"[UPDATE] htmlOutput length: {len(html_output)}")
                        print(f"[UPDATE] html_output length: {len(html_output_snake)}")
                        print(f"[UPDATE] conversation length: {len(conversation)}")
                        
                        if html_output:
                            print(f"[HTML] First 200 chars: {html_output[:200]}")
                        if html_output_snake:
                            print(f"[HTML_SNAKE] First 200 chars: {html_output_snake[:200]}")
                        if conversation:
                            print(f"[CONV] {conversation}")
                        
                        return len(html_output) > 0 or len(html_output_snake) > 0
                        
                    elif data['type'] == 'error':
                        error_msg = data.get('payload', {}).get('error', 'Unknown error')
                        print(f"[ERROR] {error_msg}")
                        return False
                    elif data['type'] == 'status':
                        status_msg = data.get('payload', {}).get('message', 'Unknown status')
                        print(f"[STATUS] {status_msg}")
                        
                except asyncio.TimeoutError:
                    if i % 5 == 0 and i > 0:
                        print(f"[WAIT] {i}s elapsed...")
                    continue
            
            print("[TIMEOUT] No valid response after 30s")
            print(f"[SUMMARY] Received {len(responses)} messages")
            for i, resp in enumerate(responses):
                print(f"  {i}: {resp['type']}")
            
            return False
            
    except Exception as e:
        print(f"[FAIL] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(debug_test())
    print(f"[RESULT] {'PASS' if success else 'FAIL'}")