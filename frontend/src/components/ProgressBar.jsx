import React from 'react';

const ProgressBar = ({ progress, currentAgent, isLoading, executionPlan }) => {
  // Use execution plan if available, otherwise show only current agent
  const defaultAgents = currentAgent ? [currentAgent] : [];
  const agents = executionPlan && executionPlan.length > 0 ? executionPlan : defaultAgents;
  
  const agentLabels = {
    supervisor: '계획',
    analytics: '분석',
    search: '검색',
    document: '문서',
    compliance: '규정'
  };
  
  const currentIndex = agents.indexOf(currentAgent);
  // Ensure percentage is always a number
  const rawPercentage = progress || ((currentIndex + 1) / Math.max(agents.length, 1)) * 100;
  const percentage = typeof rawPercentage === 'number' ? rawPercentage : Number(rawPercentage) || 0;
  
  // Don't render if no agents
  if (agents.length === 0) {
    return null;
  }
  
  return (
    <div className="progress-bar-container">
      <div className="step-indicators">
        {agents.map((agent, idx) => {
          const isCompleted = idx < currentIndex;
          const isActive = idx === currentIndex;
          const isPending = idx > currentIndex;
          
          return (
            <div 
              key={agent}
              className={`step ${
                isCompleted ? 'completed' :
                isActive ? 'active' : 'pending'
              }`}
            >
              <div className="step-circle">
                {isCompleted ? '✓' : 
                 isActive && isLoading ? (
                   <img 
                     src="/gif/spinner.gif" 
                     alt="Loading" 
                     className="step-spinner"
                   />
                 ) : (idx + 1)}
              </div>
              <div className="step-label">{agentLabels[agent]}</div>
            </div>
          );
        })}
      </div>
      
      <div className="progress-bar">
        <div 
          className="progress-fill"
          style={{ width: `${percentage}%` }}
        >
          <span className="progress-text">
            {currentIndex >= 0 && currentIndex < agents.length && (
              `${currentIndex + 1}/${agents.length} 단계`
            )}
            {` (${percentage.toFixed(0)}%)`}
          </span>
        </div>
      </div>
      
      {isLoading && currentAgent && (
        <div className="current-task">
          <img 
            src="/gif/spinner.gif" 
            alt="처리중" 
            className="task-spinner" 
          />
          <span className="task-text">
            {agentLabels[currentAgent]} 에이전트 처리 중...
          </span>
        </div>
      )}
    </div>
  );
};

export default ProgressBar;