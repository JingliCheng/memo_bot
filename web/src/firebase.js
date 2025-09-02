// Firebase configuration
import { initializeApp } from 'firebase/app';
import { getAuth, signInAnonymously, onAuthStateChanged } from 'firebase/auth';

const firebaseConfig = {
  apiKey: "AIzaSyBBUMq0dkypdT4fuqNlyhrDVUYrs5y_LwI",
  authDomain: "gen-lang-client-0574433212.firebaseapp.com",
  projectId: "gen-lang-client-0574433212",
  storageBucket: "gen-lang-client-0574433212.firebasestorage.app",
  messagingSenderId: "420724880490",
  appId: "1:420724880490:web:7985632eea355b2c2a0613",
  measurementId: "G-3YHP0X101T",
};
// Initialize Firebase with error handling
let app, auth;
try {
  app = initializeApp(firebaseConfig);
  auth = getAuth(app);
} catch (error) {
  console.error('Firebase initialization error:', error);
  // Create a mock auth object for development
  auth = {
    currentUser: null,
    signInAnonymously: () => Promise.resolve({ user: { uid: 'demo-user', getIdToken: () => Promise.resolve('demo-token') } }),
    onAuthStateChanged: (callback) => {
      // Simulate immediate authentication for demo
      setTimeout(() => callback({ uid: 'demo-user', getIdToken: () => Promise.resolve('demo-token') }), 100);
      return () => {}; // Return unsubscribe function
    }
  };
}

/**
 * Get the current user's ID token for API authentication
 * @returns {Promise<string|null>} The ID token or null if not authenticated
 */
export const getIdToken = async () => {
  const user = auth.currentUser;
  if (user) {
    try {
      return await user.getIdToken();
    } catch (error) {
      console.error('Error getting ID token:', error);
      return null;
    }
  }
  return null;
};

/**
 * Sign in anonymously and return the user
 * @returns {Promise<import('firebase/auth').User>} The authenticated user
 */
export const signInAnonymouslyUser = async () => {
  try {
    const result = await signInAnonymously(auth);
    return result.user;
  } catch (error) {
    console.error('Error signing in anonymously:', error);
    throw error;
  }
};

/**
 * Set up authentication state listener
 * @param {Function} callback - Callback function to handle auth state changes
 * @returns {Function} Unsubscribe function
 */
export const onAuthStateChange = (callback) => {
  return onAuthStateChanged(auth, callback);
};

export { auth };
export default app;
