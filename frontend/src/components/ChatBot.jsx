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
    const handleMessage = (data) => {
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
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    const handleDisconnect = () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
      setIsLoading(false);
      setCurrentAgent(null);
    };

    wsRef.current = connectWebSocket(handleMessage, handleConnect, handleDisconnect);

    return () => {
      disconnectWebSocket();
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