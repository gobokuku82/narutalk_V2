import React from 'react';

const MessageItem = ({ message, agent, data }) => {
  const renderAnalyticsContent = () => {
    const metrics = data?.metrics || {};
    const maxValue = Math.max(...Object.values(metrics).filter(v => typeof v === 'number'), 1);
    
    return (
      <div className="analytics-visual">
        <h4>📊 분석 결과</h4>
        
        {data?.kpi && (
          <div className="kpi-cards">
            {data.kpi.revenue && (
              <div className="kpi-card">
                <span className="kpi-value">{data.kpi.revenue}억</span>
                <span className="kpi-label">매출</span>
              </div>
            )}
            {data.kpi.growth && (
              <div className="kpi-card">
                <span className="kpi-value">{data.kpi.growth}%</span>
                <span className="kpi-label">성장률</span>
              </div>
            )}
            {data.kpi.conversion && (
              <div className="kpi-card">
                <span className="kpi-value">{data.kpi.conversion}%</span>
                <span className="kpi-label">전환율</span>
              </div>
            )}
          </div>
        )}
        
        {Object.keys(metrics).length > 0 && (
          <div className="bar-chart">
            {Object.entries(metrics).map(([key, value]) => (
              <div key={key} className="bar-item">
                <div className="bar-label">{key}</div>
                <div className="bar-container">
                  <div 
                    className="bar-fill"
                    style={{ width: `${(value / maxValue) * 100}%` }}
                  >
                    <span>{value}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
        
        {message.content && <div className="message-text">{message.content}</div>}
      </div>
    );
  };

  const renderSearchContent = () => {
    return (
      <div className="search-visual">
        <h4>🔍 검색 결과</h4>
        
        {data?.stats && (
          <div className="search-stats">
            총 {data.stats.total || 0}개 결과 | {data.stats.sources || 0}개 소스
          </div>
        )}
        
        {data?.results && data.results.length > 0 && (
          <div className="search-results">
            {data.results.map((result, idx) => (
              <div key={idx} className="result-card">
                <div className="result-header">
                  <span className="result-source">{result.source}</span>
                  {result.score && (
                    <span className="result-score">
                      관련도: {(result.score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <div className="result-title">{result.title}</div>
                <div className="result-snippet">{result.snippet}</div>
              </div>
            ))}
          </div>
        )}
        
        {message.content && <div className="message-text">{message.content}</div>}
      </div>
    );
  };

  const renderDocumentContent = () => {
    return (
      <div className="document-visual">
        <h4>📄 문서 분석</h4>
        
        {data?.document && (
          <div className="document-info">
            <div className="doc-meta">
              {data.document.title && <h5>{data.document.title}</h5>}
              {data.document.type && <span className="doc-type">{data.document.type}</span>}
              {data.document.date && <span className="doc-date">{data.document.date}</span>}
            </div>
            
            {data.document.sections && (
              <div className="doc-sections">
                {data.document.sections.map((section, idx) => (
                  <div key={idx} className="doc-section">
                    <h6>{section.title}</h6>
                    <p>{section.content}</p>
                  </div>
                ))}
              </div>
            )}
            
            {data.document.summary && (
              <div className="doc-summary">
                <h6>요약</h6>
                <p>{data.document.summary}</p>
              </div>
            )}
          </div>
        )}
        
        {message.content && <div className="message-text">{message.content}</div>}
      </div>
    );
  };

  const renderComplianceContent = () => {
    return (
      <div className="compliance-visual">
        <h4>✅ 규정 검토</h4>
        
        {data?.checklist && data.checklist.length > 0 && (
          <div className="compliance-checklist">
            {data.checklist.map((item, idx) => (
              <div key={idx} className={`check-item ${item.status}`}>
                <span className="check-icon">
                  {item.status === 'pass' ? '✅' : 
                   item.status === 'fail' ? '❌' : 
                   item.status === 'warning' ? '⚠️' : '⏸️'}
                </span>
                <div className="check-content">
                  <span className="check-title">{item.title}</span>
                  {item.description && (
                    <span className="check-description">{item.description}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
        
        {data?.summary && (
          <div className="compliance-summary">
            <div className="summary-stats">
              {data.summary.pass && <span className="stat-pass">통과: {data.summary.pass}</span>}
              {data.summary.fail && <span className="stat-fail">실패: {data.summary.fail}</span>}
              {data.summary.warning && <span className="stat-warning">경고: {data.summary.warning}</span>}
            </div>
          </div>
        )}
        
        {message.content && <div className="message-text">{message.content}</div>}
      </div>
    );
  };

  const renderContent = () => {
    if (message.type === 'user') {
      return (
        <div className="message-content user-message">
          <div className="message-text">{message.content}</div>
        </div>
      );
    }

    if (message.type === 'error') {
      return (
        <div className="message-content error-message">
          <span className="error-icon">⚠️</span>
          <div className="message-text">{message.content}</div>
        </div>
      );
    }

    switch (agent) {
      case 'analytics':
        return renderAnalyticsContent();
      case 'search':
        return renderSearchContent();
      case 'document':
        return renderDocumentContent();
      case 'compliance':
        return renderComplianceContent();
      case 'supervisor':
      default:
        return (
          <div className="message-content default-message">
            <div className="message-text">{message.content}</div>
          </div>
        );
    }
  };

  return (
    <div className={`message-item ${message.type}-type ${agent ? `${agent}-agent` : ''}`}>
      {message.type === 'agent' && agent && (
        <div className="message-header">
          <span className="agent-badge">{agent}</span>
          <span className="timestamp">{message.timestamp}</span>
        </div>
      )}
      
      {message.type === 'user' && (
        <div className="message-header user-header">
          <span className="user-label">You</span>
          <span className="timestamp">{message.timestamp}</span>
        </div>
      )}
      
      {renderContent()}
    </div>
  );
};

export default MessageItem;