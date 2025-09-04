import { useState, useEffect, useRef, useCallback } from 'react';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: number;
}

interface WebSocketMessage {
  type: 'chat' | 'update' | 'error' | 'status' | 'sync';
  payload: {
    content?: string;
    html_output?: string;
    htmlOutput?: string;
    error?: string;
    progress?: number;
    message?: string;
    session_id?: string;
    messages?: any[];
    current_html?: string;
    iteration_count?: number;
  };
  timestamp: number;
}

interface UseWebSocketReturn {
  messages: Message[];
  currentHtml: string;
  isProcessing: boolean;
  sendMessage: (content: string) => void;
  isConnected: boolean;
  error: string | null;
}

export const useWebSocket = (sessionId: string): UseWebSocketReturn => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentHtml, setCurrentHtml] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  
  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    
    try {
      const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
      console.log('Connecting to WebSocket:', wsUrl);
      
      wsRef.current = new WebSocket(wsUrl);
      
      wsRef.current.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setError(null);
        reconnectAttempts.current = 0;
      };
      
      wsRef.current.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);
          console.log('Received WebSocket message:', data);
          
          switch (data.type) {
            case 'sync':
              // Handle initial session sync
              if (data.payload.messages) {
                const syncedMessages = data.payload.messages.map((msg: any, index: number) => ({
                  id: `${msg.timestamp || Date.now()}-${index}`,
                  content: msg.content || msg.html_output || 'No content',
                  sender: msg.sender === 'user' ? 'user' as const : 'ai' as const,
                  timestamp: new Date(msg.timestamp).getTime() || Date.now()
                }));
                setMessages(syncedMessages);
              }
              if (data.payload.current_html) {
                setCurrentHtml(data.payload.current_html);
              }
              break;
              
            case 'update':
              // Handle HTML updates
              const htmlOutput = data.payload.htmlOutput || data.payload.html_output;
              console.log('Received HTML update:', htmlOutput ? htmlOutput.substring(0, 200) + '...' : 'No HTML content');
              
              if (htmlOutput) {
                setCurrentHtml(htmlOutput);
                
                // Add AI response to messages with better content
                let messageContent = "I've generated the HTML content! Check the preview on the right.";
                
                // Try to determine what was created based on the HTML content
                if (htmlOutput.toLowerCase().includes('business card')) {
                  messageContent = "I've created a business card for you! Check the preview on the right.";
                } else if (htmlOutput.toLowerCase().includes('landing')) {
                  messageContent = "I've created a landing page for you! Check the preview on the right.";
                } else if (htmlOutput.toLowerCase().includes('pricing')) {
                  messageContent = "I've created a pricing table for you! Check the preview on the right.";
                }
                
                const aiMessage: Message = {
                  id: `ai-${Date.now()}`,
                  content: messageContent,
                  sender: 'ai',
                  timestamp: Date.now()
                };
                setMessages(prev => [...prev, aiMessage]);
              } else {
                console.warn('Received update message without HTML content:', data);
                setError('Received empty HTML content from server');
              }
              setIsProcessing(false);
              break;
              
            case 'status':
              // Handle status updates (keep processing state active)
              console.log('Status update:', data.payload.message);
              break;
              
            case 'error':
              // Handle errors
              console.error('WebSocket error:', data.payload.error);
              setError(data.payload.error || 'Unknown error occurred');
              setIsProcessing(false);
              break;
          }
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
          setError('Failed to parse server message');
        }
      };
      
      wsRef.current.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        
        // Attempt to reconnect unless it was a clean close
        if (event.code !== 1000 && reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
          console.log(`Reconnecting in ${delay}ms...`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };
      
      wsRef.current.onerror = (err) => {
        console.error('WebSocket error:', err);
        setError('Connection error occurred');
      };
      
    } catch (err) {
      console.error('Failed to create WebSocket connection:', err);
      setError('Failed to connect to server');
    }
  }, [sessionId]);
  
  const sendMessage = useCallback((content: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('Not connected to server');
      return;
    }
    
    if (!content.trim()) {
      return;
    }
    
    try {
      // Add user message to local state immediately
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        content,
        sender: 'user',
        timestamp: Date.now()
      };
      setMessages(prev => [...prev, userMessage]);
      setIsProcessing(true);
      setError(null);
      
      // Send message to server
      const message = {
        type: 'chat',
        content,
        attachments: []
      };
      
      console.log('Sending WebSocket message:', message);
      wsRef.current.send(JSON.stringify(message));
      
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message');
      setIsProcessing(false);
    }
  }, []);
  
  // Connect on mount
  useEffect(() => {
    connect();
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close(1000);
      }
    };
  }, [connect]);
  
  return {
    messages,
    currentHtml,
    isProcessing,
    sendMessage,
    isConnected,
    error
  };
};