import React, { useState } from 'react';

const ChatInput = ({ onSendMessage, disabled }) => {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (inputText.trim() && !disabled) {
      onSendMessage(inputText.trim());
      setInputText('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="chat-input-container">
      <form onSubmit={handleSubmit} className="chat-input-form">
        <textarea
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={disabled ? "처리 중..." : "메시지를 입력하세요..."}
          disabled={disabled}
          className="chat-input"
          rows="2"
        />
        <button 
          type="submit" 
          disabled={disabled || !inputText.trim()}
          className="send-button"
        >
          <span className="send-icon">➤</span>
        </button>
      </form>
    </div>
  );
};

export default ChatInput;