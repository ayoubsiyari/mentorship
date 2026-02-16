import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { colors, colorUtils } from '../config/colors';
import { Mail, Lock, Sparkles, ChevronRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { API_BASE_URL } from '../config';
import logo from '../assets/logo4.jpg';


export default function Login() {
  const [lang, setLang] = useState('en');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [msg, setMsg] = useState('');
  const [mounted, setMounted] = useState(false);
  const [shake, setShake] = useState(false);
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [resetCode, setResetCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [forgotStep, setForgotStep] = useState(1); // 1: enter email, 2: enter code + new password
  const [forgotMsg, setForgotMsg] = useState('');
  const [forgotSuccess, setForgotSuccess] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);
  const navigate = useNavigate();
  const formRef = useRef(null);

  useEffect(() => {
    requestAnimationFrame(() => setMounted(true));
  }, []);

  useEffect(() => {
    if (shake) {
      const t = setTimeout(() => setShake(false), 500);
      return () => clearTimeout(t);
    }
  }, [shake]);

  const t = {
    en: {
      titleMain: 'Journal',
      subtitle: 'Professional Trading Intelligence',
      signInTitle: 'Log in',
      signInSub: 'Enter your email and password to continue',
      emailLabel: 'Email',
      emailPlaceholder: 'you@example.com',
      passwordLabel: 'Password',
      passwordPlaceholder: '••••••••',
      signInButton: 'Log in',
      noAccount: "Don't have an account?",
      createAccount: 'Sign up',
      loginFailed: 'Login failed',
      networkError: 'Network error, please try again',
      forgotPassword: 'Forgot password?',
      forgotTitle: 'Reset Password',
      forgotSubtitle: 'Enter your email to receive a reset code',
      sendCode: 'Send Reset Code',
      enterCode: 'Enter the code sent to your email',
      resetCodeLabel: 'Reset Code',
      newPasswordLabel: 'New Password',
      confirmPasswordLabel: 'Confirm Password',
      resetPassword: 'Reset Password',
      backToLogin: 'Back to Login',
      codeSent: 'Reset code sent! Check your email.',
      passwordReset: 'Password reset successfully! You can now login.',
      passwordMismatch: 'Passwords do not match',
      dir: 'ltr',
    },
    ar: {
      titleMain: 'سجل التداول',
      subtitle: 'ذكاء التداول الاحترافي',
      signInTitle: 'تسجيل الدخول',
      signInSub: 'أدخل بريدك الإلكتروني وكلمة المرور للمتابعة',
      emailLabel: 'البريد الإلكتروني',
      emailPlaceholder: 'مثال: you@example.com',
      passwordLabel: 'كلمة المرور',
      passwordPlaceholder: '••••••••',
      signInButton: 'تسجيل الدخول',
      noAccount: 'لا تملك حسابًا؟',
      createAccount: 'إنشاء حساب',
      loginFailed: 'فشل تسجيل الدخول',
      networkError: 'خطأ في الاتصال، حاول مرة أخرى',
      forgotPassword: 'نسيت كلمة المرور؟',
      forgotTitle: 'إعادة تعيين كلمة المرور',
      forgotSubtitle: 'أدخل بريدك الإلكتروني لاستلام رمز إعادة التعيين',
      sendCode: 'إرسال رمز إعادة التعيين',
      enterCode: 'أدخل الرمز المرسل إلى بريدك الإلكتروني',
      resetCodeLabel: 'رمز إعادة التعيين',
      newPasswordLabel: 'كلمة المرور الجديدة',
      confirmPasswordLabel: 'تأكيد كلمة المرور',
      resetPassword: 'إعادة تعيين كلمة المرور',
      backToLogin: 'العودة لتسجيل الدخول',
      codeSent: 'تم إرسال الرمز! تحقق من بريدك الإلكتروني.',
      passwordReset: 'تم إعادة تعيين كلمة المرور بنجاح! يمكنك الآن تسجيل الدخول.',
      passwordMismatch: 'كلمتا المرور غير متطابقتين',
      dir: 'rtl',
    },
  };

  const texts = t[lang];

  const { login } = useAuth();
  
  const handleLogin = async (e) => {
    e.preventDefault();
    setMsg('');
    
    // Basic validation
    if (!email || !password) {
      setMsg('Please enter both email and password');
      setShake(true);
      return;
    }
    
    try {
      // Create the request body with proper JSON formatting
      const requestBody = JSON.stringify({
        email: email.trim(),
        password: password
      });
      
      console.log('Login request body:', requestBody); // Debug log
      
      const response = await fetch('/journal/api/auth/login', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: requestBody,
        credentials: 'include' // Include cookies if needed
      });
      
      // Get response text first to handle both JSON and non-JSON responses
      const responseText = await response.text();
      let data;
      
      // Try to parse as JSON, but handle non-JSON responses gracefully
      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch (jsonError) {
        console.warn('Response is not valid JSON, but continuing with raw response');
        console.log('Raw response:', responseText);
        // If we can't parse as JSON, but the request was successful, try to proceed
        if (response.ok) {
          data = { success: true, message: 'Login successful' };
        } else {
          // For non-200 responses with non-JSON body, throw with the raw response
          throw new Error(`Server error: ${response.status} ${response.statusText}\n${responseText.substring(0, 200)}`);
        }
      }
      
      // Data is already parsed in the previous step
      
      if (response.ok) {
        if (data.user && !data.user.email_verified) {
          setMsg('Please verify your email address before logging in. Check your inbox for a verification link.');
          setShake(true);
        } else if (data.user && data.token) {
          login(data.user, data.token, data.user.is_admin);
          // Check if user has an active profile, if so go to dashboard, otherwise to profile selection
          if (data.user.has_active_profile) {
            navigate('/dashboard');
          } else {
            navigate('/select-profile');
          }
        } else {
          throw new Error('Invalid response format from server');
        }
      } else {
        setMsg(data.error || data.message || texts.loginFailed);
        setShake(true);
      }
    } catch (err) {
      console.error('Login error:', err);
      let errorMessage = texts.networkError;
      
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        errorMessage = 'Unable to connect to the server. Please check your internet connection.';
      } else if (err.message.includes('Server error')) {
        errorMessage = 'Server error occurred. Please try again later.';
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setMsg(errorMessage);
      setShake(true);
    }
  };

  const toggleLang = () => {
    setLang((prev) => (prev === 'en' ? 'ar' : 'en'));
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setForgotMsg('');
    setForgotLoading(true);

    try {
      const response = await fetch('/api/auth/forgot-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail.trim().toLowerCase() }),
      });

      const data = await response.json();

      if (response.ok) {
        setForgotStep(2);
        setForgotMsg(texts.codeSent);
        setForgotSuccess(true);
      } else {
        setForgotMsg(data.error || data.detail || 'Failed to send reset code');
        setForgotSuccess(false);
      }
    } catch (err) {
      setForgotMsg(texts.networkError);
      setForgotSuccess(false);
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setForgotMsg('');

    if (newPassword !== confirmPassword) {
      setForgotMsg(texts.passwordMismatch);
      setForgotSuccess(false);
      return;
    }

    setForgotLoading(true);

    try {
      const response = await fetch('/api/auth/reset-password', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: forgotEmail.trim().toLowerCase(),
          code: resetCode.trim(),
          new_password: newPassword,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setForgotMsg(texts.passwordReset);
        setForgotSuccess(true);
        setTimeout(() => {
          setShowForgotPassword(false);
          setForgotStep(1);
          setForgotEmail('');
          setResetCode('');
          setNewPassword('');
          setConfirmPassword('');
          setForgotMsg('');
        }, 2000);
      } else {
        setForgotMsg(data.detail || 'Failed to reset password');
        setForgotSuccess(false);
      }
    } catch (err) {
      setForgotMsg(texts.networkError);
      setForgotSuccess(false);
    } finally {
      setForgotLoading(false);
    }
  };

  const closeForgotPassword = () => {
    setShowForgotPassword(false);
    setForgotStep(1);
    setForgotEmail('');
    setResetCode('');
    setNewPassword('');
    setConfirmPassword('');
    setForgotMsg('');
    setForgotSuccess(false);
  };

  return (
    <div
      dir={texts.dir}
      className="min-h-screen flex items-center justify-center bg-[#0a0a0f] text-white overflow-hidden relative"
    >
      {/* Subtle animated background grid */}
      <div className="fixed inset-0 opacity-[0.02]">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px',
          animation: 'grid-move 20s linear infinite'
        }} />
      </div>

      {/* Gradient orb background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div 
          className="absolute top-1/4 left-1/4 w-96 h-96 rounded-full opacity-20 blur-3xl"
          style={{
            background: `radial-gradient(circle, #8b5cf6 0%, transparent 70%)`,
            transform: `translate(${0 * 0.01}px, ${0 * 0.01}px)`,
            transition: 'transform 0.5s ease-out',
            animation: 'float 8s ease-in-out infinite'
          }}
        />
        <div 
          className="absolute top-3/4 right-1/4 w-80 h-80 rounded-full opacity-15 blur-3xl"
          style={{
            background: `radial-gradient(circle, #06b6d4 0%, transparent 70%)`,
            transform: `translate(${0 * -0.008}px, ${0 * -0.008}px)`,
            transition: 'transform 0.5s ease-out',
            animation: 'float 12s ease-in-out infinite reverse'
          }}
        />
      </div>

      {/* Custom CSS animations */}
      <style jsx>{`
        @keyframes float {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-20px); }
        }
        
        @keyframes grid-move {
          0% { transform: translate(0, 0); }
          100% { transform: translate(50px, 50px); }
        }
        
        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .animate-fade-in-up {
          animation: fade-in-up 0.6s ease-out forwards;
        }
        
        @keyframes shakeX {
          0%, 100% { transform: translateX(0); }
          20%, 60% { transform: translateX(-10px); }
          40%, 80% { transform: translateX(10px); }
        }
      `}</style>

      <div
        ref={formRef}
        className={`
          relative w-full max-w-md bg-white/5 backdrop-blur-sm rounded-xl p-8 border border-white/10 shadow-2xl
          transform transition-all duration-1000 ease-out ${mounted ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}
          ${shake ? 'animate-shakeX' : ''}
        `}
      >
        {/* Language Toggle Switch */}
        <div className="absolute top-4 right-4 z-10">
          <button
            onClick={toggleLang}
            className="px-3 py-1 text-xs font-medium rounded-md bg-white/10 text-white/70 hover:bg-white/20 transition-colors"
          >
            {lang === 'en' ? 'AR' : 'EN'}
          </button>
        </div>

        {/* Logo & Heading */}
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center space-x-2 mb-4">
            <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center border border-white/10">
              <img src={logo} alt="Journal Logo" className="w-8 h-8 rounded-sm" />
            </div>
            <span className="text-2xl font-semibold text-white">{texts.titleMain}</span>
          </Link>
          <h1 className="text-3xl font-semibold text-white mb-2 animate-fade-in-up">
            {texts.signInTitle}
          </h1>
          <p className="text-white/60 text-sm animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            {texts.signInSub}
          </p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleLogin} className="space-y-6">
          {msg && (
            <div className="bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-3 rounded-md text-center text-sm">
              {msg}
              {msg.includes('verify your email') && (
                <div className="mt-2">
                  <Link 
                    to="/resend-verification" 
                    className="text-blue-400 hover:underline"
                  >
                    Resend verification email
                  </Link>
                </div>
              )}
            </div>
          )}

          <div>
            <label className="block text-white/70 text-sm font-medium mb-2" htmlFor="email">
              {texts.emailLabel}
            </label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
              <input
                type="email"
                id="email"
                placeholder={texts.emailPlaceholder}
                className="w-full pl-10 pr-3 py-2 rounded-md bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-white/70 text-sm font-medium mb-2" htmlFor="password">
              {texts.passwordLabel}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
              <input
                type="password"
                id="password"
                placeholder={texts.passwordPlaceholder}
                className="w-full pl-10 pr-3 py-2 rounded-md bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            <div className="text-right mt-1">
              <button
                type="button"
                onClick={() => setShowForgotPassword(true)}
                className="text-blue-400 hover:text-blue-300 text-xs transition-colors"
              >
                {texts.forgotPassword}
              </button>
            </div>
          </div>

          <button
            type="submit"
            className="w-full bg-white text-black py-2 rounded-md text-sm font-medium hover:bg-white/90 transition-colors flex items-center justify-center space-x-2"
          >
            <span>{texts.signInButton}</span>
            <ChevronRight className="w-4 h-4" />
          </button>
        </form>
      </div>

      {/* Forgot Password Modal */}
      {showForgotPassword && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div 
            dir={texts.dir}
            className="bg-[#0f0f1a] rounded-xl p-6 w-full max-w-md border border-white/10 shadow-2xl"
          >
            <h2 className="text-xl font-semibold text-white mb-2">{texts.forgotTitle}</h2>
            <p className="text-white/60 text-sm mb-6">
              {forgotStep === 1 ? texts.forgotSubtitle : texts.enterCode}
            </p>

            {forgotMsg && (
              <div className={`px-4 py-3 rounded-md text-sm mb-4 ${
                forgotSuccess 
                  ? 'bg-green-500/20 border border-green-500/50 text-green-300' 
                  : 'bg-red-500/20 border border-red-500/50 text-red-300'
              }`}>
                {forgotMsg}
              </div>
            )}

            {forgotStep === 1 ? (
              <form onSubmit={handleForgotPassword} className="space-y-4">
                <div>
                  <label className="block text-white/70 text-sm font-medium mb-2">
                    {texts.emailLabel}
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
                    <input
                      type="email"
                      placeholder={texts.emailPlaceholder}
                      className="w-full pl-10 pr-3 py-2 rounded-md bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm"
                      value={forgotEmail}
                      onChange={(e) => setForgotEmail(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="w-full bg-white text-black py-2 rounded-md text-sm font-medium hover:bg-white/90 transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <span>{forgotLoading ? '...' : texts.sendCode}</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={closeForgotPassword}
                  className="w-full text-white/60 hover:text-white text-sm mt-3 transition-colors"
                >
                  {texts.backToLogin}
                </button>
              </form>
            ) : (
              <form onSubmit={handleResetPassword} className="space-y-4">
                <div>
                  <label className="block text-white/70 text-sm font-medium mb-2">
                    {texts.resetCodeLabel}
                  </label>
                  <input
                    type="text"
                    placeholder="123456"
                    className="w-full px-3 py-2 rounded-md bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm text-center tracking-widest font-mono"
                    value={resetCode}
                    onChange={(e) => setResetCode(e.target.value)}
                    maxLength={6}
                    required
                  />
                </div>

                <div>
                  <label className="block text-white/70 text-sm font-medium mb-2">
                    {texts.newPasswordLabel}
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
                    <input
                      type="password"
                      placeholder="••••••••"
                      className="w-full pl-10 pr-3 py-2 rounded-md bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-white/70 text-sm font-medium mb-2">
                    {texts.confirmPasswordLabel}
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-white/50" />
                    <input
                      type="password"
                      placeholder="••••••••"
                      className="w-full pl-10 pr-3 py-2 rounded-md bg-white/10 border border-white/20 text-white placeholder-white/40 focus:outline-none focus:ring-1 focus:ring-blue-500 text-sm"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="w-full bg-white text-black py-2 rounded-md text-sm font-medium hover:bg-white/90 transition-colors flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  <span>{forgotLoading ? '...' : texts.resetPassword}</span>
                  <ChevronRight className="w-4 h-4" />
                </button>
                <button
                  type="button"
                  onClick={closeForgotPassword}
                  className="w-full text-white/60 hover:text-white text-sm mt-3 transition-colors"
                >
                  {texts.backToLogin}
                </button>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
