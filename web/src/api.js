// API service for communicating with the backend
import { getIdToken } from './firebase.js';
import cacheManager from './cacheManager.js';

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
 * @param {Function} onRawOutput - Callback for raw LLM output updates
 */
export const sendChatMessage = async (message, onChunk, onComplete, onError, onRawOutput) => {
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
    let rawOutput = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;
        
        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data:')) {
            const data = line.slice(5).trim();
            
            try {
              const parsed = JSON.parse(data);
              
              // Check if this is a completion marker
              if (parsed.done) {
                // Invalidate messages cache after new message
                const userId = token ? 'authenticated' : 'anonymous';
                cacheManager.invalidateUser('messages', userId);
                
                // Store final raw output
                if (parsed.raw_output) {
                  rawOutput = parsed.raw_output;
                  onRawOutput(rawOutput);
                }
                
                onComplete(fullResponse, rawOutput);
                return;
              }
              
              // Handle streaming chunks - now only content is sent
              if (parsed.content) {
                // Regular streaming chunk - just append to full response
                fullResponse += parsed.content;
                onChunk(parsed.content);
              }
              
              // Handle raw output updates
              if (parsed.raw_output && onRawOutput) {
                rawOutput = parsed.raw_output;
                onRawOutput(rawOutput);
              }
              
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
 * @param {number} offset - Number of items to skip (for pagination)
 * @returns {Promise<Array>} Array of memory items
 */
export const getMemories = async (limit = 12, offset = 0) => {
  const response = await apiRequest(`/api/memory?limit=${limit}&offset=${offset}`);
  const data = await response.json();
  return data.items || [];
};

/**
 * Get user's memories with caching
 * @param {number} limit - Maximum number of memories to retrieve
 * @param {number} offset - Number of items to skip (for pagination)
 * @returns {Promise<Array>} Array of memory items
 */
export const getMemoriesWithCache = async (limit = 12, offset = 0) => {
  const token = await getIdToken();
  const userId = token ? 'authenticated' : 'anonymous';
  const cacheKey = cacheManager.generateKey('memories', userId, `${limit}_${offset}`);
  
  // Try cache first
  const cached = cacheManager.get(cacheKey);
  if (cached) {
    console.log(`Using cached memories (limit: ${limit}, offset: ${offset})`);
    return cached;
  }
  
  // Fetch fresh data
  console.log(`Fetching fresh memories (limit: ${limit}, offset: ${offset})`);
  const fresh = await getMemories(limit, offset);
  
  // Cache the result
  cacheManager.set(cacheKey, fresh);
  
  return fresh;
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
  
  // Invalidate memories cache after adding new memory
  const token = await getIdToken();
  const userId = token ? 'authenticated' : 'anonymous';
  cacheManager.invalidateUser('memories', userId);
  
  return data.memory;
};

/**
 * Get user's message history
 * @param {number} limit - Maximum number of messages to retrieve
 * @param {number} offset - Number of items to skip (for pagination)
 * @returns {Promise<Array>} Array of message items
 */
export const getMessages = async (limit = 12, offset = 0) => {
  const response = await apiRequest(`/api/messages?limit=${limit}&offset=${offset}`);
  const data = await response.json();
  return data.items || [];
};

/**
 * Get user's message history with caching
 * @param {number} limit - Maximum number of messages to retrieve
 * @param {number} offset - Number of items to skip (for pagination)
 * @returns {Promise<Array>} Array of message items
 */
export const getMessagesWithCache = async (limit = 12, offset = 0) => {
  const token = await getIdToken();
  const userId = token ? 'authenticated' : 'anonymous';
  const cacheKey = cacheManager.generateKey('messages', userId, `${limit}_${offset}`);
  
  // Try cache first
  const cached = cacheManager.get(cacheKey);
  if (cached) {
    console.log(`Using cached messages (limit: ${limit}, offset: ${offset})`);
    return cached;
  }
  
  // Fetch fresh data
  console.log(`Fetching fresh messages (limit: ${limit}, offset: ${offset})`);
  const fresh = await getMessages(limit, offset);
  
  // Cache the result
  cacheManager.set(cacheKey, fresh);
  
  return fresh;
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

/**
 * Get Chroma DB data for inspection
 * @returns {Promise<Object>} Chroma DB episodes and stats
 */
export const getChromaData = async () => {
  const response = await apiRequest('/api/chroma/inspect');
  return await response.json();
};
