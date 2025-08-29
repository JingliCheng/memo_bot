// firebase.js
import { initializeApp } from "firebase/app";
import {
  getAuth,
  onAuthStateChanged,
  signInAnonymously,
  getIdToken,
  getIdTokenResult,
} from "firebase/auth";

// Your Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyBBUMq0dkypdT4fuqNlyhrDVUYrs5y_LwI",
  authDomain: "gen-lang-client-0574433212.firebaseapp.com",
  projectId: "gen-lang-client-0574433212",
  storageBucket: "gen-lang-client-0574433212.firebasestorage.app",
  messagingSenderId: "420724880490",
  appId: "1:420724880490:web:7985632eea355b2c2a0613",
  measurementId: "G-3YHP0X101T",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Ensure we have an anonymous user
export async function ensureAnonUser() {
  if (!auth.currentUser) {
    await signInAnonymously(auth);
  }
  // wait until the user object is populated
  await new Promise((resolve) => {
    const unsub = onAuthStateChanged(auth, () => {
      unsub();
      resolve();
    });
  });
  return auth.currentUser;
}

// Get Authorization header with ID token
export async function getAuthHeader() {
  const user = auth.currentUser || (await ensureAnonUser());
  
  // Check if token is expired and refresh if needed
  const token = await getIdToken(user, /* forceRefresh */ false);
  
  // If token is expired (or about to expire in next 5 minutes), force refresh
  try {
    const decodedToken = await getIdTokenResult(user);
    const expirationTime = decodedToken.expirationTime;
    const now = new Date();
    const fiveMinutesFromNow = new Date(now.getTime() + 5 * 60 * 1000);
    
    if (expirationTime <= fiveMinutesFromNow) {
      // Token is expired or about to expire, get a fresh one
      const freshToken = await getIdToken(user, /* forceRefresh */ true);
      return { Authorization: `Bearer ${freshToken}` };
    }
  } catch (error) {
    // If we can't decode the token, force refresh to be safe
    console.warn("Could not decode token, forcing refresh:", error);
    const freshToken = await getIdToken(user, /* forceRefresh */ true);
    return { Authorization: `Bearer ${freshToken}` };
  }
  
  return { Authorization: `Bearer ${token}` };
}
