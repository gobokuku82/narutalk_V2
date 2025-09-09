import React, { useState, useEffect, useRef } from 'react';
import ChatHeader from './ChatHeader';
import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ProgressBar from './ProgressBar';
import { connectWebSocket, sendMessage, disconnectWebSocket } from '../services/websocket';
import '../styles/ChatBot.css';

const ChatBot = () => {
  // Core states
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [progress, setProgress] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [threadId, setThreadId] = useState(null);
  const [executionPlan, setExecutionPlan] = useState([]);
  const [isPlanning, setIsPlanning] = useState(false);
  const [loadingMessage, setLoadingMessage] = useState('처리중...');
  const wsRef = useRef(null);

  // Helper functions
  const isPlanningAgent = (agent) => 
    ['query_analyzer', 'execution_planner'].includes(agent);

  const getAgentMessage = (agent) => ({
    query_analyzer: '생각중...',
    execution_planner: '계획중...',
    analytics: '데이터 분석 중...',
    search: '정보 검색 중...',
    document: '문서 생성 중...',
    compliance: '규정 검토 중...'
  }[agent] || '처리중...');

  // Unified state update function
  const updateAgentState = (agent) => {
    setCurrentAgent(agent);
    const planning = isPlanningAgent(agent);
    setIsPlanning(planning);
    if (!planning || agent === 'query_analyzer') {
      // Only set message for non-planning agents or initial planning
      setLoadingMessage(getAgentMessage(agent));
    }
  };

  // Effect for alternating planning messages
  useEffect(() => {
    if (isPlanning && isLoading) {
      const messages = ['생각중...', '계획중...'];
      let index = 0;
      const interval = setInterval(() => {
        setLoadingMessage(messages[index]);
        index = (index + 1) % messages.length;
      }, 1500);
      return () => clearInterval(interval);
    }
  }, [isPlanning, isLoading]);

  useEffect(() => {
    let isCleanup = false;
    
    const handleMessage = (data) => {
      if (isCleanup) return;
      console.log('Received message:', data);
      
      if (data.type === 'execution_plan') {
        // Handle execution plan from backend
        setExecutionPlan(data.agents || []);
        setIsPlanning(false);
        setMessages(prev => [...prev, {
          id: Date.now(),
          content: `실행 계획: ${(data.agents || []).join(' → ')}`,
          type: 'system',
          timestamp: new Date().toLocaleTimeString()
        }]);
      } else if (data.type === 'agent_update') {
        const agent = data.agent;
        updateAgentState(agent);
        setProgress(data.progress || 0);
        
        const newMessage = {
          id: Date.now(),
          agent: agent,
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
          setIsPlanning(false);
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
        setIsPlanning(false);
      } else if (data.type === 'progress') {
        // Handle progress update with execution plan
        if (data.execution_plan && data.execution_plan.length > 0) {
          setExecutionPlan(data.execution_plan);
        }
        const agent = data.current_agent || data.node;
        if (agent) {
          updateAgentState(agent);
        }
        
        const stepProgress = ((data.current_step + 1) / data.total_steps) * 100;
        setProgress(stepProgress || data.progress || 0);
      } else if (data.type === 'complete') {
        setIsLoading(false);
        setCurrentAgent(null);
        setProgress(100);
        setIsPlanning(false);
        if (data.thread_id) {
          setThreadId(data.thread_id);
        }
        // Reset execution plan after completion
        setTimeout(() => {
          setExecutionPlan([]);
          setProgress(0);
        }, 2000);
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
    setCurrentAgent(null);
    setExecutionPlan([]);
    setIsPlanning(true);  // Start with planning phase
    setLoadingMessage('생각중...');
    
    sendMessage({
      message: text,
      thread_id: threadId
    });
  };

  return (
    <div className="chatbot-container">
      <ChatHeader isConnected={isConnected} />
      
      <div className="chatbot-main">
        <div className="character-sidebar">
          <img 
            src="/img/naru.png" 
            alt="Naru" 
            className="naru-character"
          />
        </div>
        
        <div className="chat-content">
          <MessageList messages={messages} />
          
          {isLoading && (
            <ProgressBar 
              progress={progress}
              currentAgent={currentAgent}
              isLoading={isLoading}
              executionPlan={executionPlan}
              isPlanning={isPlanning}
              loadingMessage={loadingMessage}
            />
          )}
          
          <ChatInput 
            onSendMessage={handleSendMessage}
            disabled={isLoading || !isConnected}
          />
        </div>
      </div>
    </div>
  );
};

export default ChatBot;