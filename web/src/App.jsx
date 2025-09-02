import React, { useState, useEffect } from 'react';
import './index.css';
import { signInAnonymouslyUser, onAuthStateChange } from './firebase.js';
import { sendChatMessage, getMessages, getCurrentUser } from './api.js';
import MemoryPeek from './MemoryPeek.jsx';
import RecentMessages from './RecentMessages.jsx';

// SVG Icons as React components

const MemoryPeekIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M9 12l2 2 4-4" />
    <path d="M21 12c-1 0-3-1-3-3s2-3 3-3 3 1 3 3-2 3-3 3" />
    <path d="M3 12c1 0 3-1 3-3s-2-3-3-3-3 1-3 3 2 3 3 3" />
    <path d="M12 3c0 1-1 3-3 3s-3-2-3-3 1-3 3-3 3 2 3 3" />
    <path d="M12 21c0-1 1-3 3-3s3 2 3 3-1 3-3 3-3-2-3-3" />
  </svg>
);

const RecentMessagesIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    <path d="M13 8H7" />
    <path d="M17 12H7" />
  </svg>
);

const SettingsIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1 1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

const SendIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M22 2L11 13" />
    <path d="M22 2L15 22L11 13L2 9L22 2Z" />
  </svg>
);

/**
 * Main App component for the Talky Dino interface
 * 
 * This component renders the complete Talky Dino UI including:
 * - Header with logo and navigation icons
 * - Welcome message area
 * - Search input field
 * - Disclaimer text
 * 
 * @returns {JSX.Element} The main App component
 */
function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [userName, setUserName] = useState('User');
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [authError, setAuthError] = useState(null);
  const [showMemoryPeek, setShowMemoryPeek] = useState(false);
  const [showRecentMessages, setShowRecentMessages] = useState(false);

  /**
   * Initialize authentication and load previous messages
   */
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // Set up auth state listener
        const unsubscribe = onAuthStateChange(async (user) => {
          if (user) {
            setIsAuthenticated(true);
            setAuthError(null);
            setUserName(user.uid || 'User');
            
            // Try to get user info from backend (optional)
            try {
              const userInfo = await getCurrentUser();
              setUserName(userInfo.uid || 'User');
            } catch (error) {
              console.warn('Could not get user info from backend:', error);
              // Continue without backend user info
            }
            
            // Try to load previous messages (optional)
            try {
              const previousMessages = await getMessages(20);
              const formattedMessages = previousMessages.map(msg => ({
                id: msg.id || Date.now() + Math.random(),
                type: msg.role === 'user' ? 'user' : 'bot',
                content: msg.content,
                timestamp: msg.timestamp || new Date().toISOString()
              }));
              setMessages(formattedMessages);
            } catch (error) {
              console.warn('Could not load previous messages:', error);
              // Continue without previous messages
            }
          } else {
            setIsAuthenticated(false);
            // Try to sign in anonymously
            try {
              await signInAnonymouslyUser();
            } catch (error) {
              console.error('Authentication failed:', error);
              // Set a demo user for development
              setIsAuthenticated(true);
              setUserName('Demo User');
              setAuthError(null);
            }
          }
        });

        return unsubscribe;
      } catch (error) {
        console.error('App initialization error:', error);
        // Fallback: show UI anyway with demo user
        setIsAuthenticated(true);
        setUserName('Demo User');
        setAuthError(null);
      }
    };

    // Add a timeout to prevent hanging
    const timeoutId = setTimeout(() => {
      console.log('Authentication timeout, showing demo UI');
      setIsAuthenticated(true);
      setUserName('Demo User');
      setAuthError(null);
    }, 3000); // 3 second timeout

    initializeApp();

    return () => {
      clearTimeout(timeoutId);
    };
  }, []);

  /**
   * Handles search input changes
   * @param {React.ChangeEvent<HTMLInputElement>} event - The input change event
   */
  const handleSearchChange = (event) => {
    setSearchQuery(event.target.value);
  };

  /**
   * Handles search form submission
   * @param {React.FormEvent<HTMLFormElement>} event - The form submit event
   */
  const handleSearchSubmit = async (event) => {
    event.preventDefault();
    if (searchQuery.trim() && !isLoading && isAuthenticated) {
      const userMessage = searchQuery.trim();
      setSearchQuery('');
      setIsLoading(true);
      
      // Add user message to chat
      const newUserMessage = {
        id: Date.now(),
        type: 'user',
        content: userMessage,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, newUserMessage]);
      
      // Create a placeholder bot message for streaming
      const botMessageId = Date.now() + 1;
      const initialBotMessage = {
        id: botMessageId,
        type: 'bot',
        content: '',
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, initialBotMessage]);
      
      try {
        await sendChatMessage(
          userMessage,
          // onChunk - called for each piece of the response
          (chunk) => {
            setMessages(prev => prev.map(msg => 
              msg.id === botMessageId 
                ? { ...msg, content: msg.content + chunk }
                : msg
            ));
          },
          // onComplete - called when the response is complete
          (fullResponse) => {
            setMessages(prev => prev.map(msg => 
              msg.id === botMessageId 
                ? { ...msg, content: fullResponse }
                : msg
            ));
            setIsLoading(false);
          },
          // onError - called if there's an error
          (error) => {
            console.error('Chat API error:', error);
            // Provide a fallback response when backend is not available
            const fallbackResponse = `I received your message: "${userMessage}". This is a demo response since the backend is not currently available. In a real setup, this would connect to your Talky Dino API.`;
            setMessages(prev => prev.map(msg => 
              msg.id === botMessageId 
                ? { ...msg, content: fallbackResponse }
                : msg
            ));
            setIsLoading(false);
          }
        );
      } catch (error) {
        console.error('Error sending message:', error);
        // Provide a fallback response when backend is not available
        const fallbackResponse = `I received your message: "${userMessage}". This is a demo response since the backend is not currently available. In a real setup, this would connect to your Talky Dino API.`;
        setMessages(prev => prev.map(msg => 
          msg.id === botMessageId 
            ? { ...msg, content: fallbackResponse }
            : msg
        ));
        setIsLoading(false);
      }
    }
  };

  /**
   * Handles MemoryPeek toggle
   */
  const handleMemoryPeekToggle = () => {
    setShowMemoryPeek(!showMemoryPeek);
    console.log('MemoryPeek toggled:', !showMemoryPeek);
  };

  /**
   * Handles RecentMessages toggle
   */
  const handleRecentMessagesToggle = () => {
    setShowRecentMessages(!showRecentMessages);
    console.log('RecentMessages toggled:', !showRecentMessages);
  };

  /**
   * Handles settings button click
   */
  const handleSettingsClick = () => {
    // TODO: Implement settings functionality
    console.log('Settings clicked');
  };

  /**
   * Handles Enter key press in input
   * @param {React.KeyboardEvent<HTMLInputElement>} event - The keyboard event
   */
  const handleKeyPress = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSearchSubmit(event);
    }
  };

  // Show loading state while authenticating (only briefly)
  if (!isAuthenticated && !authError) {
    return (
      <div className="App">
        <header className="header">
          <div className="logo-container">
            <div className="logo-icon"></div>
            <span className="logo-text">Talky Dino</span>
          </div>
        </header>
        <main className="main-content">
          <div className="welcome-container">
            <h1 className="welcome-title">Connecting...</h1>
            <p className="welcome-subtitle">Setting up your chat session</p>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="App">
      {/* Header */}
      <header className="header">
        <div className="logo-container">
          <div className="logo-icon"></div>
          <span className="logo-text">Talky Dino</span>
        </div>
        
        <div className="header-icons">
          <button 
            className={`icon-button toggle-button ${showMemoryPeek ? 'active' : ''}`}
            onClick={handleMemoryPeekToggle}
            aria-label="Memory Peek"
          >
            <MemoryPeekIcon />
          </button>
          <button 
            className={`icon-button toggle-button ${showRecentMessages ? 'active' : ''}`}
            onClick={handleRecentMessagesToggle}
            aria-label="Recent Messages"
          >
            <RecentMessagesIcon />
          </button>
          <button 
            className="icon-button" 
            onClick={handleSettingsClick}
            aria-label="Settings"
          >
            <SettingsIcon />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content fade-in">
        <div className={`content-layout ${showMemoryPeek || showRecentMessages ? 'with-sidebar' : 'centered'}`}>
          {/* Main Chat Area */}
          <div className="chat-main">
            {messages.length === 0 ? (
              <div className="welcome-container">
                <h1 className="welcome-title">Welcome back, {userName}</h1>
                <p className="welcome-subtitle">How can I help you today?</p>
              </div>
            ) : (
              <div className="chat-container">
                <div className="messages-list">
                  {messages.map((message) => (
                    <div key={message.id} className={`message ${message.type}`}>
                      <div className="message-header">
                        <div className="message-avatar">
                          {message.type === 'user' ? (
                            <div className="user-avatar">You</div>
                          ) : (
                            <div className="bot-avatar">
                              <span className="dino-icon">🦕</span>
                            </div>
                          )}
                        </div>
                        <div className="message-name">
                          {message.type === 'user' ? 'You' : 'Talky Dino'}
                        </div>
                      </div>
                      <div className="message-content">
                        {message.content || (isLoading && message.type === 'bot' ? (
                          <div className="typing-indicator">
                            <span></span>
                            <span></span>
                            <span></span>
                          </div>
                        ) : message.content)}
                      </div>
                      <div className="message-timestamp">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <form className="input-container" onSubmit={handleSearchSubmit}>
              <div className="input-wrapper">
          <input
            type="text"
                  className="search-input"
                  placeholder="Ask me anything..."
                  value={searchQuery}
                  onChange={handleSearchChange}
                  onKeyPress={handleKeyPress}
                  disabled={isLoading}
                  aria-label="Chat input"
          />
          <button
            type="submit"
                  className="send-button"
                  disabled={!searchQuery.trim() || isLoading}
                  aria-label="Send message"
          >
                  <SendIcon />
          </button>
              </div>
        </form>

            <p className="disclaimer">
              🦕 Talky Dino loves to chat and have fun conversations with you!
            </p>
          </div>

          {/* Right Sidebar */}
          <div className="sidebar">
            {showMemoryPeek && <MemoryPeek />}
            {showRecentMessages && <RecentMessages />}
          </div>
      </div>
      </main>
    </div>
  );
}

export default App;
