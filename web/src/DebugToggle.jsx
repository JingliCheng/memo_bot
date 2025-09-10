import React from 'react';

/**
 * Debug Toggle component for showing raw LLM output
 * 
 * This component provides a toggle to show/hide the raw LLM output
 * for debugging purposes. It displays the raw output in a formatted
 * text area that can be copied and analyzed.
 * 
 * @param {Object} props - Component props
 * @param {boolean} props.isVisible - Whether the debug panel is visible
 * @param {string} props.rawOutput - The raw LLM output to display
 * @param {Function} props.onToggle - Callback when toggle is clicked
 * @returns {JSX.Element} The DebugToggle component
 */
export default function DebugToggle({ isVisible, rawOutput, onToggle }) {
  return (
    <div className="debug-toggle-panel">
      <div className="debug-toggle-header">
        <h3>🐛 Debug Mode</h3>
        <button 
          className={`debug-toggle-button ${isVisible ? 'active' : ''}`}
          onClick={onToggle}
          aria-label="Toggle debug mode"
        >
          {isVisible ? 'Hide Raw Output' : 'Show Raw Output'}
        </button>
      </div>
      
      {isVisible && (
        <div className="debug-content">
          <div className="debug-info">
            <p>This shows the raw LLM output before any parsing or formatting.</p>
            <p>Use this for debugging prompt engineering and response parsing.</p>
          </div>
          
          <div className="raw-output-container">
            <div className="raw-output-header">
              <span>Raw LLM Output:</span>
              <button 
                className="copy-button"
                onClick={() => {
                  navigator.clipboard.writeText(rawOutput || '');
                  // Could add a toast notification here
                }}
                title="Copy to clipboard"
              >
                📋 Copy
              </button>
            </div>
            
            <textarea
              className="raw-output-textarea"
              value={rawOutput || 'No raw output available yet. Send a message to see the raw LLM response.'}
              readOnly
              rows={8}
              placeholder="Raw LLM output will appear here..."
            />
          </div>
          
          {rawOutput && (
            <div className="debug-stats">
              <div className="stat-item">
                <span className="stat-label">Characters:</span>
                <span className="stat-value">{rawOutput.length}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Words:</span>
                <span className="stat-value">{rawOutput.split(/\s+/).filter(word => word.length > 0).length}</span>
              </div>
              <div className="stat-item">
                <span className="stat-label">Lines:</span>
                <span className="stat-value">{rawOutput.split('\n').length}</span>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
