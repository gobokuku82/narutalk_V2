import React from 'react';

const ChatHeader = ({ isConnected }) => {
  return (
    <div className="chat-header">
      <div className="header-content">
        <div className="header-info">
          <h1 className="chat-title">
            <img 
              src="/img/main.png" 
              alt="Narutalk Logo" 
              className="header-logo"
            />
            Narutalk Sales AI
          </h1>
          <div className="connection-status">
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
            <span className="status-text">
              {isConnected ? '연결됨' : '연결 중...'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatHeader;