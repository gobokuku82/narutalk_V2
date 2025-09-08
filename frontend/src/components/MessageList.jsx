import React, { useEffect, useRef } from 'react';
import MessageItem from './MessageItem';

const MessageList = ({ messages }) => {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="message-list">
      {messages.length === 0 ? (
        <div className="empty-state">
          <p>안녕하세요! 영업 지원 AI입니다.</p>
          <p>어떤 도움이 필요하신가요?</p>
        </div>
      ) : (
        messages.map((message) => (
          <MessageItem 
            key={message.id} 
            message={message}
            agent={message.agent}
            data={message.data}
          />
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default MessageList;