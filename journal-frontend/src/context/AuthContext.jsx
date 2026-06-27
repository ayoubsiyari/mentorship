import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize auth state from localStorage on mount
  useEffect(() => {
    console.log('🔍 AuthContext - Initializing auth state (SIMPLE VERSION)');
    
    // Check for admin login parameter
    const urlParams = new URLSearchParams(window.location.search);
    const adminLoginKey = urlParams.get('admin_login');
    
    if (adminLoginKey) {
      console.log('🔍 AuthContext - Admin login detected, checking for session data');
      const adminLoginData = localStorage.getItem(adminLoginKey);
      
      if (adminLoginData) {
        try {
          const loginData = JSON.parse(adminLoginData);
          console.log('✅ AuthContext - Admin login data found, logging in as user:', loginData.user.email);
          
          // Set the admin login session
          setUser(loginData.user);
          setToken(loginData.token);
          setIsAdmin(loginData.user.is_admin);
          
          // Store in localStorage
          localStorage.setItem('token', loginData.token);
          localStorage.setItem('refresh_token', loginData.refresh_token);
          localStorage.setItem('is_admin', loginData.user.is_admin.toString());
          localStorage.setItem('talaria_current_user', JSON.stringify(loginData.user));
          
          // Set admin login session flag
          localStorage.setItem('admin_login_session', 'true');
          
          // Clear cached profile from admin session so target user's profiles load fresh
          localStorage.removeItem('talaria_activeProfile');
          
          // Remove the admin_login parameter from URL
          const newUrl = window.location.pathname;
          window.history.replaceState({}, document.title, newUrl);
          
          // Clean up the admin login key after a short delay to ensure it's processed
          setTimeout(() => {
            localStorage.removeItem(adminLoginKey);
          }, 2000);
          
          console.log('✅ AuthContext - Admin login session established successfully');
          
          // Add a small delay to ensure state is properly set before initializing
          setTimeout(() => {
            setIsInitialized(true);
          }, 100);
          
          return;
        } catch (error) {
          console.error('❌ AuthContext - Error parsing admin login data:', error);
          localStorage.removeItem(adminLoginKey);
        }
      } else {
        console.log('❌ AuthContext - Admin login key found but no data in localStorage');
      }
    }
    
    const storedToken = localStorage.getItem('token');
    const storedIsAdmin = localStorage.getItem('is_admin') === 'true';
    
    console.log('🔍 AuthContext - Stored token exists:', !!storedToken);
    console.log('🔍 AuthContext - Stored isAdmin:', storedIsAdmin);
    console.log('🔍 AuthContext - Processing regular authentication flow');
    
    if (storedToken) {
      setToken(storedToken);
      setIsAdmin(storedIsAdmin);
      
      // Try to decode user info from token and validate with backend
      try {
        const payload = JSON.parse(atob(storedToken.split('.')[1]));
        
        // Check if token is expired
        const currentTime = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp < currentTime) {
          console.log('⚠️ AuthContext - Token expired, clearing session');
          localStorage.removeItem('token');
          localStorage.removeItem('is_admin');
          setIsInitialized(true);
          return;
        }
        
        setUser({
          id: payload.sub,
          is_admin: storedIsAdmin
        });
        console.log('✅ AuthContext - Successfully decoded token for user:', payload.sub);
        
        // Note: Skip backend validation on page reload to prevent logout
        // Token will be validated naturally when making API calls
        console.log('✅ AuthContext - Token loaded from localStorage, will validate on first API call');
        
      } catch (error) {
        console.error('❌ AuthContext - Error decoding token:', error);
        // Clear corrupted session
        localStorage.removeItem('token');
        localStorage.removeItem('is_admin');
      }
    } else {
      console.log('ℹ️ AuthContext - No stored token found');
    }
    setIsInitialized(true);
  }, []);

  const login = (userData, authToken, adminStatus = false) => {
    console.log('🔄 AuthContext - Login called (SIMPLE VERSION)');
    setUser(userData);
    setToken(authToken);
    setIsAdmin(adminStatus);
    
    // Store in localStorage (OLD SIMPLE WAY)
    localStorage.setItem('token', authToken);
    localStorage.setItem('is_admin', adminStatus.toString());
    
    console.log('✅ AuthContext - Stored session (simple version)');
  };

  const logout = () => {
    setUser(null);
    setToken(null);
    setIsAdmin(false);
    
    // Clear localStorage (ALL VERSIONS)
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('is_admin');
    localStorage.removeItem('talaria_current_user');
    localStorage.removeItem('admin_login_session');
    
    // Clear any user-specific tokens that might exist
    Object.keys(localStorage).forEach(key => {
      if (key.startsWith('talaria_') && key.includes('_token')) {
        localStorage.removeItem(key);
      }
      if (key.startsWith('talaria_') && key.includes('_is_admin')) {
        localStorage.removeItem(key);
      }
    });
    
    console.log('✅ AuthContext - Logout complete (cleaned all storage)');
  };

  const isAuthenticated = !!token;
  
  console.log('🔍 AuthContext - Current state (SIMPLE):', { 
    hasToken: !!token, 
    isAuthenticated, 
    hasUser: !!user, 
    isAdmin,
    isInitialized
  });
  
  return (
    <AuthContext.Provider value={{ user, token, isAdmin, isAuthenticated, isInitialized, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
