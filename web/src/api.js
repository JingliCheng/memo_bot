// API service for communicating with the backend
import { getIdToken } from './firebase.js';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Make an authenticated API request
 * @param {string} endpoint - The API endpoint
 * @param {Object} options - Fetch options
 * @returns {Promise<Response>} The fetch response
 */
const apiRequest = async (endpoint, options = {}) => {
  const token = await getIdToken();
  
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const url = `${API_BASE_URL}${endpoint}`;
  
  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API request failed: ${response.status} ${errorText}`);
  }

  return response;
};

/**
 * Send a chat message and get streaming response
 * @param {string} message - The user's message
 * @param {Function} onChunk - Callback for each chunk of the response
 * @param {Function} onComplete - Callback when the response is complete
 * @param {Function} onError - Callback for errors
 */
export const sendChatMessage = async (message, onChunk, onComplete, onError) => {
  try {
    const token = await getIdToken();
    
    const response = await fetch(`${API_BASE_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data:')) {
            const data = line.slice(5).trim();
            
            if (data === '[DONE]') {
              onComplete(fullResponse);
              return;
            }
            
            try {
              const parsed = JSON.parse(data);
              fullResponse += parsed;
              onChunk(parsed);
            } catch (e) {
              // Skip invalid JSON chunks
              console.warn('Invalid JSON chunk:', data);
            }
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  } catch (error) {
    console.error('Chat API error:', error);
    onError(error);
  }
};

/**
 * Get user's memories
 * @param {number} limit - Maximum number of memories to retrieve
 * @returns {Promise<Array>} Array of memory items
 */
export const getMemories = async (limit = 12) => {
  const response = await apiRequest(`/api/memory?limit=${limit}`);
  const data = await response.json();
  return data.items || [];
};

/**
 * Add a new memory
 * @param {Object} memory - The memory object to add
 * @returns {Promise<Object>} The saved memory
 */
export const addMemory = async (memory) => {
  const response = await apiRequest('/api/memory', {
    method: 'POST',
    body: JSON.stringify(memory),
  });
  const data = await response.json();
  return data.memory;
};

/**
 * Get user's message history
 * @param {number} limit - Maximum number of messages to retrieve
 * @returns {Promise<Array>} Array of message items
 */
export const getMessages = async (limit = 12) => {
  const response = await apiRequest(`/api/messages?limit=${limit}`);
  const data = await response.json();
  return data.items || [];
};

/**
 * Get current user info
 * @returns {Promise<Object>} User information
 */
export const getCurrentUser = async () => {
  const response = await apiRequest('/whoami');
  return await response.json();
};

/**
 * Check if the API is healthy
 * @returns {Promise<Object>} Health status
 */
export const checkHealth = async () => {
  const response = await apiRequest('/health');
  return await response.json();
};
