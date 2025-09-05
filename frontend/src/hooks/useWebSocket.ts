import { useState, useEffect, useRef, useCallback } from 'react';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'ai';
  timestamp: number;
}

interface WebSocketMessage {
  type: 'chat' | 'update' | 'dual_response' | 'thinking' | 'error' | 'status' | 'sync';
  payload: {
    content?: string;
    html_output?: string;
    htmlOutput?: string;
    conversation?: string;
    error?: string;
    progress?: number;
    message?: string;
    session_id?: string;
    messages?: Message[];
    current_html?: string;
    iteration_count?: number;
    artifact?: {
      id: string;
      version: number;
      title: string;
      type: string;
      changes: string[];
    };
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
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
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
                const syncedMessages = data.payload.messages.map((msg, index: number) => ({
                  id: `${msg.timestamp || Date.now()}-${index}`,
                  content: msg.content || 'No content',
                  sender: msg.sender === 'user' ? 'user' as const : 'ai' as const,
                  timestamp: msg.timestamp || Date.now()
                }));
                setMessages(syncedMessages);
              }
              if (data.payload.current_html) {
                setCurrentHtml(data.payload.current_html);
              }
              break;
              
            case 'dual_response': {
              // Handle the new conversational dual response architecture
              const htmlOutput = data.payload.htmlOutput;
              const conversation = data.payload.conversation;
              const artifact = data.payload.artifact;
              
              console.log('Received dual response:', {
                htmlLength: htmlOutput?.length || 0,
                conversationLength: conversation?.length || 0,
                artifactVersion: artifact?.version,
                changes: artifact?.changes
              });
              
              // Update HTML artifact in rendering panel
              if (htmlOutput) {
                setCurrentHtml(htmlOutput);
                console.log('Updated HTML artifact:', htmlOutput.substring(0, 100) + '...');
              }
              
              // Add conversational response to chat
              if (conversation && conversation.trim()) {
                setMessages(prev => {
                  const aiMessage: Message = {
                    id: `ai-${Date.now()}-v${artifact?.version || 1}`,
                    content: conversation.trim(),
                    sender: 'ai',
                    timestamp: Date.now()
                  };
                  
                  console.log('Adding AI conversation message:', aiMessage.content.substring(0, 100) + '...');
                  return [...prev, aiMessage];
                });
              }
              
              // Log artifact information
              if (artifact) {
                console.log('Artifact updated:', {
                  title: artifact.title,
                  version: artifact.version,
                  type: artifact.type,
                  changes: artifact.changes
                });
              }
              
              setIsProcessing(false);
              setError(null);
              break;
            }

            case 'update': {
              // Legacy update handling for backward compatibility
              const htmlOutput = data.payload.htmlOutput || data.payload.html_output;
              const conversation = data.payload.conversation;
              
              console.log('Received legacy update:', htmlOutput ? htmlOutput.substring(0, 200) + '...' : 'No HTML content');
              
              if (htmlOutput) {
                setCurrentHtml(htmlOutput);
              }
              
              if (conversation && conversation.trim()) {
                setMessages(prev => {
                  const aiMessage: Message = {
                    id: `ai-${Date.now()}`,
                    content: conversation.trim(),
                    sender: 'ai',
                    timestamp: Date.now()
                  };
                  
                  return [...prev, aiMessage];
                });
              }
              
              setIsProcessing(false);
              break;
            }

            case 'thinking': {
              // Handle thinking/progress status updates
              console.log('AI is thinking:', data.payload.message);
              // Keep processing state active during thinking
              setIsProcessing(true);
              setError(null);
              break;
            }
              
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