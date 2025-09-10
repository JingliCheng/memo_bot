// cacheManager.js
/**
 * Cache manager for client-side caching of API responses
 * Handles user-specific caching with automatic invalidation
 */

const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
const CACHE_PREFIX = 'memo_bot_cache';

class CacheManager {
  constructor() {
    this.prefix = CACHE_PREFIX;
  }

  /**
   * Generate cache key for user-specific data
   * @param {string} dataType - Type of data (memories, messages, etc.)
   * @param {string} userId - User ID
   * @param {string|number} params - Additional parameters (limit, etc.)
   * @returns {string} Cache key
   */
  generateKey(dataType, userId, params = '') {
    return `${this.prefix}:${dataType}:${userId}:${params}`;
  }

  /**
   * Get cached data if it exists and is not expired
   * @param {string} key - Cache key
   * @returns {any|null} Cached data or null if not found/expired
   */
  get(key) {
    try {
      const cached = localStorage.getItem(key);
      if (!cached) return null;

      const { data, timestamp } = JSON.parse(cached);
      if (Date.now() - timestamp > CACHE_DURATION) {
        // Cache expired, remove it
        localStorage.removeItem(key);
        return null;
      }

      return data;
    } catch (error) {
      console.warn('Cache get error:', error);
      // Remove corrupted cache entry
      localStorage.removeItem(key);
      return null;
    }
  }

  /**
   * Set data in cache with timestamp
   * @param {string} key - Cache key
   * @param {any} data - Data to cache
   */
  set(key, data) {
    try {
      const cacheEntry = {
        data,
        timestamp: Date.now()
      };
      
      // Check storage size before setting
      const entrySize = JSON.stringify(cacheEntry).length;
      const currentSize = this.getTotalSize();
      const maxSize = 4 * 1024 * 1024; // 4MB limit
      
      if (currentSize + entrySize > maxSize) {
        console.warn('Cache storage limit approaching, cleaning up...');
        this.cleanup();
      }
      
      localStorage.setItem(key, JSON.stringify(cacheEntry));
    } catch (error) {
      console.warn('Cache set error:', error);
      // If localStorage is full, try to clean up old entries
      this.cleanup();
    }
  }

  /**
   * Get total size of all cache entries
   * @returns {number} Total size in bytes
   */
  getTotalSize() {
    try {
      let totalSize = 0;
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(this.prefix)) {
          const value = localStorage.getItem(key);
          if (value) {
            totalSize += value.length;
          }
        }
      }
      return totalSize;
    } catch (error) {
      console.warn('Error calculating cache size:', error);
      return 0;
    }
  }

  /**
   * Invalidate all cache entries matching a pattern
   * @param {string} pattern - Pattern to match (e.g., 'memories:user123')
   */
  invalidate(pattern) {
    try {
      const keysToRemove = [];
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.includes(pattern)) {
          keysToRemove.push(key);
        }
      }
      
      keysToRemove.forEach(key => {
        localStorage.removeItem(key);
        console.log(`Invalidated cache: ${key}`);
      });
    } catch (error) {
      console.warn('Cache invalidation error:', error);
    }
  }

  /**
   * Invalidate user-specific cache
   * @param {string} dataType - Type of data to invalidate
   * @param {string} userId - User ID
   */
  invalidateUser(dataType, userId) {
    const pattern = `${this.prefix}:${dataType}:${userId}`;
    this.invalidate(pattern);
  }

  /**
   * Clean up expired cache entries
   */
  cleanup() {
    try {
      const now = Date.now();
      const keysToRemove = [];
      
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(this.prefix)) {
          try {
            const cached = localStorage.getItem(key);
            if (cached) {
              const { timestamp } = JSON.parse(cached);
              if (now - timestamp > CACHE_DURATION * 2) { // 2x cache duration
                keysToRemove.push(key);
              }
            }
          } catch (e) {
            // Corrupted entry, remove it
            keysToRemove.push(key);
          }
        }
      }
      
      keysToRemove.forEach(key => localStorage.removeItem(key));
      
      if (keysToRemove.length > 0) {
        console.log(`Cleaned up ${keysToRemove.length} expired cache entries`);
      }
    } catch (error) {
      console.warn('Cache cleanup error:', error);
    }
  }

  /**
   * Get cache statistics
   * @returns {Object} Cache statistics
   */
  getStats() {
    try {
      let totalEntries = 0;
      let expiredEntries = 0;
      const now = Date.now();
      
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith(this.prefix)) {
          totalEntries++;
          try {
            const cached = localStorage.getItem(key);
            if (cached) {
              const { timestamp } = JSON.parse(cached);
              if (now - timestamp > CACHE_DURATION) {
                expiredEntries++;
              }
            }
          } catch (e) {
            expiredEntries++;
          }
        }
      }
      
      return {
        totalEntries,
        expiredEntries,
        validEntries: totalEntries - expiredEntries
      };
    } catch (error) {
      console.warn('Cache stats error:', error);
      return { totalEntries: 0, expiredEntries: 0, validEntries: 0 };
    }
  }
}

// Create singleton instance
const cacheManager = new CacheManager();

// Run cleanup on page load
if (typeof window !== 'undefined') {
  cacheManager.cleanup();
}

export default cacheManager;
