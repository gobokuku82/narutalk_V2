import React, { useState, useEffect, useRef } from 'react';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ProgressBar from './ProgressBar';
import { connectWebSocket, sendMessage, disconnectWebSocket } from '../services/websocket';
import '../styles/ChatBot.css';

const ChatBot = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [progress, setProgress] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    let isCleanup = false;
    
    const handleMessage = (data) => {
      if (isCleanup) return;
      console.log('Received message:', data);
      
      if (data.type === 'agent_update') {
        setCurrentAgent(data.agent);
        setProgress(data.progress || 0);
        
        const newMessage = {
          id: Date.now(),
          agent: data.agent,
          content: data.message || '',
          data: data.data || {},
          timestamp: new Date().toLocaleTimeString(),
          type: 'agent'
        };
        
        setMessages(prev => [...prev, newMessage]);
        
        if (data.status === 'completed') {
          setIsLoading(false);
          setCurrentAgent(null);
          setProgress(100);
        }
      } else if (data.type === 'error') {
        setMessages(prev => [...prev, {
          id: Date.now(),
          content: data.message || 'An error occurred',
          type: 'error',
          timestamp: new Date().toLocaleTimeString()
        }]);
        setIsLoading(false);
        setCurrentAgent(null);
      } else if (data.type === 'complete') {
        setIsLoading(false);
        setCurrentAgent(null);
        setProgress(100);
        if (data.thread_id) {
          setThreadId(data.thread_id);
        }
      }
    };

    const handleConnect = () => {
      if (isCleanup) return;
      console.log('WebSocket connected in ChatBot');
      setIsConnected(true);
    };

    const handleDisconnect = () => {
      if (isCleanup) return;
      console.log('WebSocket disconnected in ChatBot');
      setIsConnected(false);
      setIsLoading(false);
      setCurrentAgent(null);
    };

    // Only connect if not already connected
    if (!wsRef.current) {
      console.log('Initializing WebSocket connection...');
      wsRef.current = connectWebSocket(handleMessage, handleConnect, handleDisconnect);
    }

    return () => {
      console.log('ChatBot cleanup triggered');
      isCleanup = true;
      // Don't disconnect immediately - only on actual unmount
      // This prevents premature disconnection during StrictMode double-render
    };
  }, []);

  // Cleanup on actual unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        console.log('ChatBot unmounting, disconnecting WebSocket');
        disconnectWebSocket();
        wsRef.current = null;
      }
    };
  }, []);

  const handleSendMessage = (text) => {
    const userMessage = {
      id: Date.now(),
      content: text,
      type: 'user',
      timestamp: new Date().toLocaleTimeString()
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setProgress(0);
    setCurrentAgent('supervisor');
    
    sendMessage({
      message: text,
      thread_id: threadId
    });
  };

  return (
    <div className="chatbot-container">
      <ChatHeader isConnected={isConnected} />
      
      <MessageList messages={messages} />
      
      {isLoading && (
        <ProgressBar 
          progress={progress}
          currentAgent={currentAgent}
          isLoading={isLoading}
        />
      )}
      
      <ChatInput 
        onSendMessage={handleSendMessage}
        disabled={isLoading || !isConnected}
      />
    </div>
  );
};

export default ChatBot;