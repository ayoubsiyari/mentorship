import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';
import { countries } from '../data/countries';
import { colors, colorUtils } from '../config/colors';
import { isFeatureEnabled, FEATURE_GROUPS } from '../config/featureFlags';
import { useFeatureFlags } from '../context/FeatureFlagsContext';
import FEATURE_FLAGS from '../config/featureFlags';
import {
  User,
  Mail,
  Lock,
  Image,
  Save,
  LogOut,
  Eye,
  EyeOff,
  Camera,
  Check,
  X,
  AlertCircle,
  Crown,
  Users,
  Trash2,
  UserPlus,
  BarChart3,
  Activity,
  FileText,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  Settings as SettingsIcon,
  Server,
  TrendingUp,
  RefreshCw,
  Download,
  Bell,
  Shield,
  Database,
  Plus,
  Filter,
  MoreHorizontal,
  Edit,
  Copy,
  ExternalLink,
  Zap,
  Star,
  Award,
  Target,
  Calendar,
  Clock,
  Globe,
  Wifi,
  Power,
  HardDrive,
  Cpu,
  Server as MemoryIcon,
  Phone,
  MapPin,
  CheckCircle,
  UserCheck,
  AlertTriangle,
  Ban,
  BookOpen,
  LogIn
} from 'lucide-react';
import { PieChart as RePieChart, Pie, Cell, ResponsiveContainer, Tooltip as ReTooltip, Legend as ReLegend } from 'recharts';
import BulkUserImport from '../components/BulkUserImport';
import BulkEmailManager from '../components/BulkEmailManager';
import NewsletterManager from '../components/NewsletterManager';

export default function Settings() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [profileImage, setProfileImage] = useState('');
  const [previewImage, setPreviewImage] = useState('');
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalData, setOriginalData] = useState({ email: '', profileImage: '' });
  
  // Admin state
  const [isAdmin, setIsAdmin] = useState(false);
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newFullName, setNewFullName] = useState('');
  const [newPhone, setNewPhone] = useState('');
  const [newCountry, setNewCountry] = useState('');
  const [newSelectedCountry, setNewSelectedCountry] = useState(null);
  const [newSelectedPhoneCode, setNewSelectedPhoneCode] = useState(null);
  const [newShowCountryDropdown, setNewShowCountryDropdown] = useState(false);
  const [newShowPhoneCodeDropdown, setNewShowPhoneCodeDropdown] = useState(false);
  const [newProfileImage, setNewProfileImage] = useState('');
  const [newIsAdmin, setNewIsAdmin] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(null);
  
  // Enhanced admin state
  const [activeAdminTab, setActiveAdminTab] = useState('dashboard');
  const [dashboardData, setDashboardData] = useState(null);
  const [logs, setLogs] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [pagination, setPagination] = useState({ page: 1, per_page: 10000, total: 0 });
  
  // Advanced admin features
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserModal, setShowUserModal] = useState(false);
  
  // Feature flags state
  const [localFeatureFlags, setLocalFeatureFlags] = useState({});
  const [isSavingFlags, setIsSavingFlags] = useState(false);
  const [flagsMessage, setFlagsMessage] = useState('');
  const [showSystemModal, setShowSystemModal] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [userTypeFilter, setUserTypeFilter] = useState('all'); // 'all', 'journal', 'no-journal', 'mentorship'
  const [bootcampEmails, setBootcampEmails] = useState([]);
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [refreshInterval, setRefreshInterval] = useState(30000);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [exportFormat, setExportFormat] = useState('csv');
  const [bulkActions, setBulkActions] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [showBulkActions, setShowBulkActions] = useState(false);
  const [systemMetrics, setSystemMetrics] = useState({
    cpu: 0,
    memory: 0,
    disk: 0,
    network: 0,
    uptime: 0,
    loadAverage: [0, 0, 0]
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);

  // Add state for editing user
  const [editUser, setEditUser] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const [editLoading, setEditLoading] = useState(false);
  const [editError, setEditError] = useState('');

  // Email count state
  const [emailPrefix, setEmailPrefix] = useState('');
  const [emailCountResult, setEmailCountResult] = useState(null);
  const [emailCountLoading, setEmailCountLoading] = useState(false);

  // Server monitoring state
  const [serverMonitoring, setServerMonitoring] = useState(null);
  const [serverMonitoringLoading, setServerMonitoringLoading] = useState(false);
  const [attackHistory, setAttackHistory] = useState(null);
  const [healthSubTab, setHealthSubTab] = useState('overview'); // overview, security, services, intrusion
  const [intrusionData, setIntrusionData] = useState(null);
  const [securityAudit, setSecurityAudit] = useState(null);
  const [intrusionLoading, setIntrusionLoading] = useState(false);

  // Application security state
  const [securityStats, setSecurityStats] = useState(null);
  const [blockedIPs, setBlockedIPs] = useState([]);
  const [failedLogins, setFailedLogins] = useState([]);
  const [securityLogs, setSecurityLogs] = useState([]);
  const [newBlockIP, setNewBlockIP] = useState('');
  const [newBlockReason, setNewBlockReason] = useState('');
  const [blockingIP, setBlockingIP] = useState(false);
  const [hostSecurityData, setHostSecurityData] = useState(null);

  // Security settings state
  const [securitySettings, setSecuritySettings] = useState({});
  const [securitySettingsLoading, setSecuritySettingsLoading] = useState(false);
  const [savingSettings, setSavingSettings] = useState(false);

  // Geography analytics state
  const [geographyData, setGeographyData] = useState(null);
  const [geographyLoading, setGeographyLoading] = useState(false);
  const [geographyFilter, setGeographyFilter] = useState('all');

  // Analytics state
  const [analyticsOverview, setAnalyticsOverview] = useState(null);
  const [userGrowth, setUserGrowth] = useState([]);
  const [tradeActivity, setTradeActivity] = useState([]);
  const [topSymbols, setTopSymbols] = useState([]);
  const [topUsers, setTopUsers] = useState([]);
  const [groupAnalytics, setGroupAnalytics] = useState([]);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Feature flags context
  const { refreshFeatureFlags } = useFeatureFlags();

  // Handler to open edit modal
  const handleEditUser = (user) => {
    setEditUser({ ...user });
    setShowEditModal(true);
    setEditError('');
  };

  // Handler to save user edits
  const handleSaveEditUser = async () => {
    if (!editUser) return;
    setEditLoading(true);
    setEditError('');
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/users/${editUser.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          email: editUser.email,
          full_name: editUser.full_name,
          country: editUser.country,
          is_admin: editUser.is_admin,
          email_verified: editUser.email_verified
        })
      });
      if (res.ok) {
        setShowEditModal(false);
        fetchUsers();
      } else {
        const data = await res.json();
        setEditError(data.error || 'Failed to update user');
      }
    } catch (err) {
      setEditError('Error updating user');
    } finally {
      setEditLoading(false);
    }
  };

  // ─── 1. On mount: fetch current profile ────────────────────────────────────────
  useEffect(() => {
    const fetchProfile = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setMsg('You are not logged in.');
        return;
      }

      try {
        const res = await fetch(`${API_BASE_URL}/auth/profile`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`
          }
        });

        if (res.status === 401 || res.status === 422) {
          setMsg('Invalid or expired token. Please log in again.');
          setTimeout(() => (window.location.href = '/login'), 2000);
          return;
        }

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }

        const data = await res.json();
        setEmail(data.email || '');
        setProfileImage(data.profile_image || '');
        setPreviewImage(data.profile_image || '');
        setOriginalData({
          email: data.email || '',
          profileImage: data.profile_image || ''
        });
        
        // Check if user is admin
        const adminStatus = localStorage.getItem('is_admin') === 'true';
        setIsAdmin(adminStatus);
        
        // If admin, fetch users and admin data
        if (adminStatus) {
          fetchUsers();
          fetchDashboardData();
          fetchLogs();
          fetchSystemHealth();
          fetchServerMonitoring();
          fetchBootcampEmails();
        }
        
        setMsg('');
      } catch (err) {
        console.error('Settings.jsx: fetchProfile error →', err);
        setMsg('Failed to load profile. Please try again.');
      }
    };

    fetchProfile();
  }, []);

  // ─── 2. Track "unsaved changes" ───────────────────────────────────────────────
  useEffect(() => {
    const changed =
      email !== originalData.email ||
      password.trim() !== '' ||
      profileImage !== originalData.profileImage;
    setHasChanges(changed);
  }, [email, password, profileImage, originalData]);

  // ─── 3. Handle form submission (update profile) ───────────────────────────────
  const handleSave = async (e) => {
    console.log('🔴 handleSave called');
    e.preventDefault();
    setMsg('');
    setLoading(true);

    const token = localStorage.getItem('token');
    if (!token) {
      setMsg('You must be logged in.');
      setLoading(false);
      return;
    }

    if (!email.trim()) {
      setMsg('Email cannot be empty.');
      setLoading(false);
      return;
    }

    try {
      const payload = {
        email: email.trim().toLowerCase(),
        ...(password.trim() ? { password: password.trim() } : {}),
        ...(profileImage.trim() ? { profile_image: profileImage.trim() } : {})
      };

      const res = await fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      const data = await res.json();

      if (res.ok) {
        setMsg('Profile updated successfully!');
        if (payload.profile_image) {
          setPreviewImage(payload.profile_image);
        }
        setPassword('');
        setOriginalData({
          email: payload.email,
          profileImage: payload.profile_image || originalData.profileImage
        });
        // Clear success message after 3 seconds
        setTimeout(() => setMsg(''), 3000);
      } else {
        setMsg(data.error || data.msg || 'Failed to update profile.');
      }
    } catch (err) {
      console.error('Settings.jsx: update error →', err);
      setMsg('Server error while saving. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // ─── 4. Handle image URL change ───────────────────────────────────────────────
  const handleImageChange = (e) => {
    const url = e.target.value;
    setProfileImage(url);
    setPreviewImage(url);
  };

  // ─── 5. Handle logout ─────────────────────────────────────────────────────────
  const handleLogout = () => {
    if (hasChanges) {
      if (!window.confirm('You have unsaved changes. Are you sure you want to logout?')) {
        return;
      }
    }
    localStorage.removeItem('token');
    localStorage.removeItem('is_admin');
    window.location.href = '/login';
  };

  // ─── 6. Admin functions ───────────────────────────────────────────────────────
  const fetchUsers = async (page = 1, search = '') => {
    setLoadingUsers(true);
    try {
      const token = localStorage.getItem('token');
      
      // Build query parameters
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: pagination.per_page.toString()
      });
      
      if (search) {
        params.append('search', search);
      }
      
      const res = await fetch(`${API_BASE_URL}/admin/users?${params}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
        // Update pagination state from API response
        if (data.pagination) {
          setPagination(data.pagination);
        }
      } else {
        console.error('Failed to fetch users');
      }
    } catch (err) {
      console.error('Error fetching users:', err);
    } finally {
      setLoadingUsers(false);
    }
  };

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setMsg('');

    if (!newEmail || !newPassword) {
      setMsg('Email and password are required.');
      return;
    }

    setIsCreating(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/users`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          email: newEmail,
          password: newPassword,
          full_name: newFullName,
          phone: getNewPhoneWithCode(),
          country: newCountry,
          profile_image: newProfileImage,
          is_admin: newIsAdmin
        })
      });
      
      const data = await res.json();

      if (res.ok) {
        setMsg('User created successfully!');
        setNewEmail('');
        setNewPassword('');
        setNewFullName('');
        setNewPhone('');
        setNewCountry('');
        setNewSelectedCountry(null);
        setNewSelectedPhoneCode(null);
        setNewProfileImage('');
        setNewIsAdmin(false);
        fetchUsers(); // Refresh user list
      } else {
        setMsg(data.error || 'Failed to create user');
      }
    } catch (err) {
      console.error('Error creating user:', err);
      setMsg('Error creating user');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user? This action cannot be undone.')) return;

    setIsDeleting(userId);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        setMsg('User deleted successfully!');
        fetchUsers(); // Refresh user list
      } else {
        const data = await res.json();
        setMsg(data.error || 'Failed to delete user');
      }
    } catch (err) {
      console.error('Error deleting user:', err);
      setMsg('Error deleting user');
    } finally {
      setIsDeleting(null);
    }
  };

  const loginAsUser = async (userId) => {
    const targetUser = users.find(u => u.id === userId);
    if (!targetUser) return;
    
    const confirmed = window.confirm(
      `Are you sure you want to login as ${targetUser.email}?\n\nThis will open a new window where you can act as this user. You can close the window to return to your admin session.`
    );
    
    if (!confirmed) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/admin/users/${userId}/login-as`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate login token');
      }

      const data = await response.json();
      
      // Store the tokens in localStorage for the new window
      const loginData = {
        token: data.token,
        refresh_token: data.refresh_token,
        user: data.user
      };
      
      // Create a unique key for this login session
      const sessionKey = `admin_login_${Date.now()}`;
      localStorage.setItem(sessionKey, JSON.stringify(loginData));
      
      // Open new private window with the login data
      const newWindow = window.open(
        `${window.location.origin}?admin_login=${sessionKey}`,
        '_blank',
        'width=1200,height=800,scrollbars=yes,resizable=yes'
      );
      
                 if (newWindow) {
             // Clear the session key after a longer delay to ensure the new window has time to process it
             setTimeout(() => {
               localStorage.removeItem(sessionKey);
             }, 10000);
           }
      
    } catch (err) {
      setMsg(err.message);
    }
  };

  const getMessageType = () => {
    if (msg.includes('successfully')) return 'success';
    if (msg.includes('Invalid') || msg.includes('Failed') || msg.includes('error')) return 'error';
    return 'info';
  };

  // Enhanced admin functions
  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/dashboard/enhanced`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setDashboardData(data);
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
    }
  };

  const fetchLogs = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/logs?limit=50`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setLogs(data.logs || []);
      }
    } catch (err) {
      console.error('Error fetching logs:', err);
    }
  };

  const fetchSystemHealth = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/system/health`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setSystemHealth(data);
      }
    } catch (err) {
      console.error('Error fetching system health:', err);
    }
  };

  const fetchServerMonitoring = async () => {
    setServerMonitoringLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/monitoring/overview`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setServerMonitoring(data);
      }
    } catch (err) {
      console.error('Error fetching server monitoring:', err);
      setServerMonitoringLoading(false);
    }
  };

  const fetchIntrusionDetection = async () => {
    setIntrusionLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
      
      const [intrusionRes, auditRes] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/monitoring/intrusion-detection`, { headers }),
        fetch(`${API_BASE_URL}/admin/monitoring/security-audit`, { headers })
      ]);
      
      if (intrusionRes.ok) {
        const data = await intrusionRes.json();
        setIntrusionData(data);
      }
      if (auditRes.ok) {
        const data = await auditRes.json();
        setSecurityAudit(data);
      }
    } catch (err) {
      console.error('Error fetching intrusion detection:', err);
    } finally {
      setIntrusionLoading(false);
    }
  };

  const fetchBootcampEmails = async () => {
    try {
      const response = await fetch('/api/bootcamp/registrations/emails');
      if (response.ok) {
        const data = await response.json();
        setBootcampEmails(data.emails || []);
      }
    } catch (err) {
      console.error('Failed to fetch bootcamp registrations:', err);
    }
  };

  const fetchSecurityData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
      
      const [statsRes, blockedRes, failedRes, logsRes, hostSecRes] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/security/stats`, { headers }),
        fetch(`${API_BASE_URL}/admin/security/blocked-ips`, { headers }),
        fetch(`${API_BASE_URL}/admin/security/failed-logins`, { headers }),
        fetch(`${API_BASE_URL}/admin/security/logs?limit=20`, { headers }),
        fetch(`${API_BASE_URL}/admin/monitoring/security`, { headers })
      ]);
      
      if (statsRes.ok) {
        const data = await statsRes.json();
        setSecurityStats(data);
      }
      if (blockedRes.ok) {
        const data = await blockedRes.json();
        setBlockedIPs(data.blocked_ips || []);
      }
      if (failedRes.ok) {
        const data = await failedRes.json();
        setFailedLogins(data.failed_logins || []);
      }
      if (logsRes.ok) {
        const data = await logsRes.json();
        setSecurityLogs(data.logs || []);
      }
      if (hostSecRes.ok) {
        const data = await hostSecRes.json();
        setHostSecurityData(data);
      }
    } catch (err) {
      console.error('Error fetching security data:', err);
    }
  };

  const handleBlockIP = async () => {
    if (!newBlockIP.trim()) return;
    setBlockingIP(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/security/block-ip`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          ip_address: newBlockIP.trim(),
          reason: newBlockReason.trim() || 'Manually blocked by admin',
          is_permanent: false,
          duration_hours: 24
        })
      });
      if (res.ok) {
        setNewBlockIP('');
        setNewBlockReason('');
        fetchSecurityData();
      }
    } catch (err) {
      console.error('Error blocking IP:', err);
    } finally {
      setBlockingIP(false);
    }
  };

  const handleUnblockIP = async (blockId) => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/security/unblock-ip/${blockId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchSecurityData();
      }
    } catch (err) {
      console.error('Error unblocking IP:', err);
    }
  };

  const fetchAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const headers = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` };
      
      const [overviewRes, growthRes, tradesRes, symbolsRes, usersRes, groupsRes] = await Promise.all([
        fetch(`${API_BASE_URL}/admin/analytics/overview`, { headers }),
        fetch(`${API_BASE_URL}/admin/analytics/user-growth?days=30`, { headers }),
        fetch(`${API_BASE_URL}/admin/analytics/trade-activity?days=30`, { headers }),
        fetch(`${API_BASE_URL}/admin/analytics/top-symbols?limit=10`, { headers }),
        fetch(`${API_BASE_URL}/admin/analytics/user-activity?limit=10`, { headers }),
        fetch(`${API_BASE_URL}/admin/analytics/groups`, { headers })
      ]);
      
      if (overviewRes.ok) setAnalyticsOverview(await overviewRes.json());
      if (growthRes.ok) {
        const data = await growthRes.json();
        setUserGrowth(data.data || []);
      }
      if (tradesRes.ok) {
        const data = await tradesRes.json();
        setTradeActivity(data.data || []);
      }
      if (symbolsRes.ok) {
        const data = await symbolsRes.json();
        setTopSymbols(data.symbols || []);
      }
      if (usersRes.ok) {
        const data = await usersRes.json();
        setTopUsers(data.users || []);
      }
      if (groupsRes.ok) {
        const data = await groupsRes.json();
        setGroupAnalytics(data.groups || []);
      }
    } catch (err) {
      console.error('Error fetching analytics:', err);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchUsers(1, searchTerm);
  };

  const handlePageChange = (newPage) => {
    fetchUsers(newPage, searchTerm);
  };

  // Fetch security settings
  const fetchSecuritySettings = async () => {
    setSecuritySettingsLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/settings/security`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setSecuritySettings(data.settings || {});
      }
    } catch (err) {
      console.error('Error fetching security settings:', err);
    } finally {
      setSecuritySettingsLoading(false);
    }
  };

  // Save security settings
  const saveSecuritySettings = async () => {
    setSavingSettings(true);
    try {
      const token = localStorage.getItem('token');
      const settingsToSave = {};
      Object.keys(securitySettings).forEach(key => {
        settingsToSave[key] = securitySettings[key].value;
      });
      
      const res = await fetch(`${API_BASE_URL}/admin/settings/security`, {
        method: 'PUT',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify(settingsToSave)
      });
      
      if (res.ok) {
        setMsg('Security settings saved successfully!');
        setTimeout(() => setMsg(''), 3000);
      }
    } catch (err) {
      console.error('Error saving security settings:', err);
      setMsg('Failed to save settings');
    } finally {
      setSavingSettings(false);
    }
  };

  // Reset security settings to defaults
  const resetSecuritySettings = async () => {
    if (!window.confirm('Reset all security settings to defaults?')) return;
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/settings/security/reset`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        fetchSecuritySettings();
        setMsg('Settings reset to defaults');
        setTimeout(() => setMsg(''), 3000);
      }
    } catch (err) {
      console.error('Error resetting settings:', err);
    }
  };

  // Update a single security setting
  const updateSecuritySetting = (key, value) => {
    setSecuritySettings(prev => ({
      ...prev,
      [key]: { ...prev[key], value }
    }));
  };

  // Fetch geography analytics
  const fetchGeographyData = async (filter = 'all') => {
    setGeographyLoading(true);
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/analytics/geography?filter=${filter}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setGeographyData(data);
      }
    } catch (err) {
      console.error('Error fetching geography data:', err);
    } finally {
      setGeographyLoading(false);
    }
  };

  // Advanced admin functions
  const fetchSystemMetrics = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/system/metrics`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setSystemMetrics(data);
      }
    } catch (err) {
      console.error('Error fetching system metrics:', err);
    }
  };

  const fetchRecentActivity = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/activity?limit=10`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setRecentActivity(data.activities || []);
      }
    } catch (err) {
      console.error('Error fetching recent activity:', err);
    }
  };

  const handleBulkAction = async (action) => {
    if (selectedUsers.length === 0) return;
    
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/users/bulk`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          action,
          user_ids: selectedUsers
        })
      });
      
      if (res.ok) {
        setMsg(`Bulk ${action} completed successfully!`);
        setSelectedUsers([]);
        fetchUsers();
      } else {
        const data = await res.json();
        setMsg(data.error || `Failed to perform bulk ${action}`);
      }
    } catch (err) {
      setMsg(`Error performing bulk ${action}`);
    }
  };

  const exportUsers = async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/users/export?format=${exportFormat}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `users-export-${new Date().toISOString().split('T')[0]}.${exportFormat}`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    } catch (err) {
      setMsg('Error exporting users');
    }
  };

  const toggleUserSelection = (userId) => {
    setSelectedUsers(prev => 
      prev.includes(userId) 
        ? prev.filter(id => id !== userId)
        : [...prev, userId]
    );
  };

  const selectAllUsers = () => {
    setSelectedUsers(users.map(user => user.id));
  };

  const clearUserSelection = () => {
    setSelectedUsers([]);
  };

  const handleNewCountrySelect = (countryData) => {
    setNewSelectedCountry(countryData);
    setNewCountry(countryData.name);
    setNewShowCountryDropdown(false);
  };

  const handleNewPhoneCodeSelect = (countryData) => {
    setNewSelectedPhoneCode(countryData);
    setNewShowPhoneCodeDropdown(false);
  };

  const getNewPhoneWithCode = () => {
    if (newSelectedPhoneCode && newPhone) {
      return `${newSelectedPhoneCode.phoneCode}${newPhone.replace(/^0+/, '')}`;
    }
    return newPhone;
  };

  // Feature flags functions
  const handleToggleFeature = (featureName) => {
    console.log('🔄 Toggling feature:', featureName);
    console.log('📊 Current state before toggle:', localFeatureFlags);
    console.log('🔍 Feature exists in state:', featureName in localFeatureFlags);
    console.log('🔍 Current value:', localFeatureFlags[featureName]);
    
    setLocalFeatureFlags(prev => {
      const newValue = !prev[featureName];
      console.log('🔄 New value will be:', newValue);
      const newState = {
        ...prev,
        [featureName]: newValue
      };
      console.log('📊 New state after toggle:', newState);
      return newState;
    });
  };

  const handleToggleFeatureGroup = (groupName, enabled) => {
    const group = FEATURE_GROUPS[groupName];
    if (!group) return;

    const updatedFlags = { ...localFeatureFlags };
    group.forEach(feature => {
      updatedFlags[feature] = enabled;
    });
    setLocalFeatureFlags(updatedFlags);
  };

  const handleSaveFeatureFlags = async () => {
    setIsSavingFlags(true);
    setFlagsMessage('');

    try {
      console.log('💾 Saving feature flags...');
      console.log('📊 Current localFeatureFlags state:', localFeatureFlags);
      
      // Prepare flags data for backend
      const flagsData = Object.entries(localFeatureFlags).map(([name, enabled]) => ({
        name,
        enabled,
        category: getFeatureCategory(name)
      }));
      
      console.log('📤 Sending flags data to backend:', flagsData);

      const response = await fetch(`${API_BASE_URL}/feature-flags/bulk`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ flags: flagsData })
      });

      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          // Refresh global feature flags for users
          await refreshFeatureFlags();
          
          // Reload admin feature flags to ensure UI stays in sync
          const flagsResponse = await fetch(`${API_BASE_URL}/feature-flags`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });
          
          if (flagsResponse.ok) {
            const flagsData = await flagsResponse.json();
            if (flagsData.success && flagsData.flags) {
              // Convert array of flag objects to simple object format
              const flagsObject = {};
              flagsData.flags.forEach(flag => {
                flagsObject[flag.name] = flag.enabled;
              });
              setLocalFeatureFlags(flagsObject);
              console.log('✅ Admin feature flags reloaded after save:', flagsObject);
            }
          }
          
          setFlagsMessage('Feature flags updated successfully!');
          setTimeout(() => setFlagsMessage(''), 3000);
        } else {
          setFlagsMessage('Error: ' + (result.error || 'Unknown error'));
        }
      } else {
        setFlagsMessage('Error saving feature flags: ' + response.statusText);
      }
    } catch (error) {
      setFlagsMessage('Error saving feature flags: ' + error.message);
    } finally {
      setIsSavingFlags(false);
    }
  };

  const getFeatureCategory = (featureName) => {
    if (['DASHBOARD', 'JOURNAL', 'TRADES', 'SETTINGS'].includes(featureName)) {
      return 'core';
    } else if (featureName.startsWith('ANALYTICS')) {
      return 'analytics';
    } else if (['AI_DASHBOARD', 'STRATEGY_BUILDER', 'IMPORT_TRADES', 'NOTES', 'LEARN', 'PROFILE_MANAGEMENT'].includes(featureName)) {
      return 'advanced';
    } else if (featureName === 'ADMIN_PANEL') {
      return 'admin';
    } else if (featureName.startsWith('TEST')) {
      return 'test';
    }
    return 'other';
  };

  const handleResetFeatureFlags = async () => {
    try {
      setFlagsMessage('');
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/feature-flags/initialize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        if (data.success) {
          // Convert array of flag objects to simple object format
          const flagsObject = {};
          data.flags.forEach(flag => {
            flagsObject[flag.name] = flag.enabled;
          });
          setLocalFeatureFlags(flagsObject);
          setFlagsMessage('✅ Feature flags reset to defaults successfully!');
        } else {
          setFlagsMessage('❌ Error resetting feature flags: ' + (data.error || 'Unknown error'));
        }
      } else {
        setFlagsMessage('❌ Error resetting feature flags: ' + res.statusText);
      }
    } catch (error) {
      console.error('Error resetting feature flags:', error);
      setFlagsMessage('❌ Error resetting feature flags: ' + error.message);
    }
  };

  // Initialize feature flags
  useEffect(() => {
    if (isAdmin) {
      const initializeFlags = async () => {
        console.log('🚀 Initializing feature flags for admin...');
        try {
          // Fetch current flags from backend API
          const response = await fetch(`${API_BASE_URL}/feature-flags`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });
          
          console.log('📡 Response status:', response.status);
          
          if (response.ok) {
            const data = await response.json();
            console.log('📥 Received data:', data);
            if (data.success && data.flags) {
              // Convert array of flag objects to simple object format
              const flagsObject = {};
              data.flags.forEach(flag => {
                flagsObject[flag.name] = flag.enabled;
              });
              console.log('🔄 Converting to object format:', flagsObject);
              setLocalFeatureFlags(flagsObject);
              console.log('✅ Admin feature flags loaded from backend:', flagsObject);
            } else {
              console.warn('⚠️ No feature flags found in backend response');
              // Fall back to fetching from the static config as backup
              await refreshFeatureFlags();
              const { default: currentFlags } = await import('../config/featureFlags');
              setLocalFeatureFlags(currentFlags);
            }
          } else {
            console.warn('⚠️ Failed to fetch admin feature flags, using fallback');
            // Fall back to fetching from the static config as backup
            await refreshFeatureFlags();
            const { default: currentFlags } = await import('../config/featureFlags');
            setLocalFeatureFlags(currentFlags);
          }
        } catch (error) {
          console.error('❌ Error loading feature flags:', error);
          // Fall back to fetching from the static config as backup
          await refreshFeatureFlags();
          const { default: currentFlags } = await import('../config/featureFlags');
          setLocalFeatureFlags(currentFlags);
        }
      };
      
      initializeFlags();
    }
  }, [isAdmin]);

  // Auto-refresh functionality
  useEffect(() => {
    if (!isAdmin || !autoRefresh) return;

    const refreshData = async () => {
      if (activeAdminTab === 'dashboard') {
        fetchDashboardData();
        fetchSystemMetrics();
      } else if (activeAdminTab === 'users') {
        fetchUsers();
      } else if (activeAdminTab === 'logs') {
        fetchLogs();
      } else if (activeAdminTab === 'health') {
        fetchSystemHealth();
        fetchServerMonitoring();
      } else if (activeAdminTab === 'feature-flags') {
        // Refresh feature flags from backend
        try {
          await refreshFeatureFlags();
          // Reload admin feature flags to ensure UI stays in sync
          const flagsResponse = await fetch(`${API_BASE_URL}/feature-flags`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });
          
          if (flagsResponse.ok) {
            const flagsData = await flagsResponse.json();
            if (flagsData.success && flagsData.flags) {
              // Convert array of flag objects to simple object format
              const flagsObject = {};
              flagsData.flags.forEach(flag => {
                flagsObject[flag.name] = flag.enabled;
              });
              setLocalFeatureFlags(flagsObject);
            }
          }
        } catch (error) {
          console.error('Error refreshing feature flags:', error);
        }
      }
      fetchRecentActivity();
    };

    const interval = setInterval(refreshData, refreshInterval);

    return () => clearInterval(interval);
  }, [isAdmin, autoRefresh, activeAdminTab, refreshInterval]);

  // Email count function
  const handleEmailCount = async (prefix = null) => {
    const searchPrefix = prefix || emailPrefix;
    if (!searchPrefix.trim()) return;
    
    setEmailCountLoading(true);
    setEmailCountResult(null);
    
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${API_BASE_URL}/admin/users/count-email-prefix?prefix=${encodeURIComponent(searchPrefix)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (res.ok) {
        const data = await res.json();
        setEmailCountResult(data);
      } else {
        const errorData = await res.json();
        setEmailCountResult({
          prefix: searchPrefix,
          count: 0,
          sample_emails: [],
          message: `Error: ${errorData.error || res.statusText}`
        });
      }
    } catch (error) {
      console.error('Error counting users by email prefix:', error);
      setEmailCountResult({
        prefix: searchPrefix,
        count: 0,
        sample_emails: [],
        message: `Error: ${error.message}`
      });
    } finally {
      setEmailCountLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0a1628]">
      {/* Main Container */}
      <div className="w-full px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Header Section */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-white">Settings</h1>
          <p className="text-gray-400 mt-1">Manage your account and system preferences</p>
        </div>

        {/* Status Message */}
        {msg && (
          <div className="mb-8 max-w-4xl mx-auto">
            <div
              className={`p-5 rounded-2xl flex items-center gap-4 shadow-lg border-l-4 backdrop-blur-sm ${
                getMessageType() === 'success'
                  ? 'bg-emerald-50/90 border-emerald-500 text-emerald-800'
                  : getMessageType() === 'error'
                  ? 'bg-red-50/90 border-red-500 text-red-800'
                  : 'bg-blue-50/90 border-blue-500 text-blue-800'
              }`}
            >
              <div className={`p-2 rounded-full ${
                getMessageType() === 'success' ? 'bg-emerald-100' :
                getMessageType() === 'error' ? 'bg-red-100' : 'bg-blue-100'
              }`}>
                {getMessageType() === 'success' && <Check className="w-5 h-5 text-emerald-600" />}
                {getMessageType() === 'error' && <X className="w-5 h-5 text-red-600" />}
                {getMessageType() === 'info' && <AlertCircle className="w-5 h-5 text-blue-600" />}
              </div>
              <span className="font-semibold text-lg">{msg}</span>
            </div>
          </div>
        )}

        {/* Administrator Dashboard Section - Now below Profile Information */}
        {isAdmin && (
          <div className="space-y-8">
            
            {/* Admin Header */}
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-semibold text-white">Admin Dashboard</h2>
                <p className="text-gray-500 text-sm">System management</p>
              </div>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`px-4 py-2 rounded-lg text-sm transition-all ${
                  autoRefresh 
                    ? 'bg-blue-500/20 text-blue-400' 
                    : 'bg-[#1e3a5f] text-gray-400 hover:text-white'
                }`}
              >
                {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
              </button>
            </div>

            {/* Admin Tabs */}
            <div className="bg-[#1e3a5f] rounded-xl border border-[#2d4a6f] overflow-hidden">
              {/* Tab Navigation */}
              <div className="flex overflow-x-auto border-b border-[#2d4a6f] bg-[#0a1628]">
                {[
                  { id: 'dashboard', label: 'Overview' },
                  { id: 'users', label: 'Users' },
                  { id: 'logs', label: 'Logs' },
                  { id: 'health', label: 'Health' },
                  { id: 'analytics', label: 'Analytics' },
                  { id: 'geography', label: 'Geography' },
                  { id: 'feature-flags', label: 'Features' },
                  { id: 'bulk-email', label: 'Email' },
                  { id: 'newsletter', label: 'Newsletter' },
                  { id: 'settings', label: 'Settings' }
                ].map(tab => {
                  const isActive = activeAdminTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveAdminTab(tab.id)}
                      className={`px-5 py-3 text-sm font-medium transition-all whitespace-nowrap ${
                        isActive
                          ? 'text-white border-b-2 border-blue-500'
                          : 'text-gray-500 hover:text-gray-300'
                      }`}
                    >
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {/* Tab Content */}
              <div className={activeAdminTab === 'bulk-email' || activeAdminTab === 'newsletter' ? 'p-0' : 'p-6'}>
                {/* Dashboard Tab */}
                {activeAdminTab === 'dashboard' && (
                  <div className="space-y-6">
                    {/* Key Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Users</p>
                        <p className="text-2xl font-semibold text-white mt-1">{dashboardData?.total_users || users.length}</p>
                      </div>
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Active (30d)</p>
                        <p className="text-2xl font-semibold text-white mt-1">{dashboardData?.active_users || 0}</p>
                      </div>
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Trades</p>
                        <p className="text-2xl font-semibold text-white mt-1">{dashboardData?.total_trades || 0}</p>
                      </div>
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Admins</p>
                        <p className="text-2xl font-semibold text-white mt-1">{dashboardData?.admin_users_count || 0}</p>
                      </div>
                    </div>

                    {/* Secondary Metrics */}
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Profiles</p>
                        <p className="text-2xl font-semibold text-white mt-1">{dashboardData?.total_profiles || 0}</p>
                      </div>
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Journals</p>
                        <p className="text-2xl font-semibold text-white mt-1">{dashboardData?.total_journals || 0}</p>
                      </div>
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Status</p>
                        <p className="text-2xl font-semibold text-green-400 mt-1">{systemHealth?.status || 'Healthy'}</p>
                      </div>
                      <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                        <p className="text-gray-500 text-xs uppercase tracking-wide">Features</p>
                        <p className="text-2xl font-semibold text-white mt-1">{Object.values(localFeatureFlags).filter(Boolean).length}/{Object.keys(localFeatureFlags).length}</p>
                      </div>
                    </div>

                    {/* System Status & Quick Actions */}
                    <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
                      {/* System Status */}
                      <div className="xl:col-span-2 bg-[#0a1628] rounded-lg border border-[#2d4a6f] p-5">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-sm font-medium text-white">System Status</h3>
                          <button
                            onClick={() => {
                              fetchSystemHealth();
                              fetchSystemMetrics();
                            }}
                            className="text-gray-500 hover:text-white text-xs"
                          >
                            Refresh
                          </button>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          {[
                            { name: 'Database', status: 'Connected' },
                            { name: 'Email', status: 'Active' },
                            { name: 'API', status: 'Running' },
                            { name: 'Frontend', status: 'Online' }
                          ].map((service, index) => (
                            <div key={index} className="flex items-center gap-3 p-3 bg-[#1e3a5f] rounded-lg">
                              <div className="w-2 h-2 rounded-full bg-green-400"></div>
                              <div>
                                <p className="text-sm text-white">{service.name}</p>
                                <p className="text-xs text-gray-500">{service.status}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Quick Actions */}
                      <div className="bg-[#0a1628] rounded-lg border border-[#2d4a6f] p-5">
                        <h3 className="text-sm font-medium text-white mb-4">Quick Actions</h3>
                        <div className="space-y-2">
                          <button onClick={() => setActiveAdminTab('users')} className="w-full p-2 text-left text-sm text-gray-400 hover:text-white hover:bg-[#1e3a5f] rounded">Add User</button>
                          <button onClick={exportUsers} className="w-full p-2 text-left text-sm text-gray-400 hover:text-white hover:bg-[#1e3a5f] rounded">Export Data</button>
                          <button onClick={() => setActiveAdminTab('logs')} className="w-full p-2 text-left text-sm text-gray-400 hover:text-white hover:bg-[#1e3a5f] rounded">View Logs</button>
                        </div>
                      </div>

                      {/* Performance */}
                      <div className="bg-[#0a1628] rounded-lg border border-[#2d4a6f] p-5">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="text-sm font-medium text-white">Performance</h3>
                          <button onClick={() => { fetchSystemHealth(); fetchSystemMetrics(); }} className="text-gray-500 hover:text-white text-xs">Refresh</button>
                        </div>
                        {systemMetrics ? (
                          <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                              <div className="bg-[#1e3a5f] rounded-lg p-4 border border-[#2d4a6f]">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-sm font-medium text-gray-400">CPU Usage</span>
                                  <span className="text-sm font-bold text-white">{systemMetrics.cpu?.percent || 0}%</span>
                                </div>
                                <div className="w-full bg-[#0a1628] rounded-full h-2">
                                  <div 
                                    className="bg-blue-500 h-2 rounded-full transition-all duration-300" 
                                    style={{ width: `${systemMetrics.cpu?.percent || 0}%` }}
                                  ></div>
                                </div>
                              </div>
                              
                              <div className="bg-[#1e3a5f] rounded-lg p-4 border border-[#2d4a6f]">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-sm font-medium text-gray-400">Memory Usage</span>
                                  <span className="text-sm font-bold text-white">{systemMetrics.memory?.percent || 0}%</span>
                                </div>
                                <div className="w-full bg-[#0a1628] rounded-full h-2">
                                  <div 
                                    className="bg-green-500 h-2 rounded-full transition-all duration-300" 
                                    style={{ width: `${systemMetrics.memory?.percent || 0}%` }}
                                  ></div>
                                </div>
                              </div>
                            </div>
                            
                            <div className="bg-[#1e3a5f] rounded-lg p-4 border border-[#2d4a6f]">
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-sm font-medium text-gray-400">Disk Usage</span>
                                <span className="text-sm font-bold text-white">{Math.round(systemMetrics.disk?.percent || 0)}%</span>
                              </div>
                              <div className="w-full bg-[#0a1628] rounded-full h-2">
                                <div 
                                  className="bg-purple-500 h-2 rounded-full transition-all duration-300" 
                                  style={{ width: `${systemMetrics.disk?.percent || 0}%` }}
                                ></div>
                              </div>
                            </div>
                            
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div className="bg-[#1e3a5f] rounded-lg p-4 border border-[#2d4a6f]">
                                <div className="text-gray-400">Uptime</div>
                                <div className="font-bold text-white">{systemMetrics.uptime?.formatted || 'N/A'}</div>
                              </div>
                              <div className="bg-[#1e3a5f] rounded-lg p-4 border border-[#2d4a6f]">
                                <div className="text-gray-400">Load Average</div>
                                <div className="font-bold text-white">
                                  {systemMetrics.load_average ? systemMetrics.load_average[0].toFixed(2) : 'N/A'}
                                </div>
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="text-center py-8">
                            <Activity className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                            <p className="text-gray-400">Click refresh to load system metrics</p>
                          </div>
                        )}
                      </div>

                      {/* Recent Activity */}
                      <div className="bg-[#0a1628] rounded-xl border border-[#2d4a6f] p-6">
                        <div className="flex items-center justify-between mb-6">
                          <div className="flex items-center gap-3">
                            <div className="p-3 bg-green-500/20 rounded-lg">
                              <Clock className="w-6 h-6 text-green-400" />
                            </div>
                            <h3 className="text-lg font-bold text-white">Recent Activity</h3>
                          </div>
                          <button
                            onClick={fetchRecentActivity}
                            className="text-green-400 hover:text-green-300 transition-colors p-2 rounded-lg hover:bg-green-500/20"
                          >
                            <RefreshCw className="w-5 h-5" />
                          </button>
                        </div>
                        
                        <div className="space-y-3 max-h-80 overflow-y-auto">
                          {recentActivity && recentActivity.length > 0 ? (
                            recentActivity.slice(0, 10).map((activity, index) => (
                              <div key={index} className="bg-[#1e3a5f] rounded-lg p-4 border border-[#2d4a6f]">
                                <div className="flex items-start justify-between">
                                  <div className="flex-1">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-sm font-semibold text-white">
                                        {activity.action.replace(/_/g, ' ')}
                                      </span>
                                      <span className="text-xs text-gray-500">
                                        {new Date(activity.timestamp).toLocaleTimeString()}
                                      </span>
                                    </div>
                                    <p className="text-sm text-gray-400">{activity.details}</p>
                                    <p className="text-xs text-gray-500 mt-1">User: {activity.user}</p>
                                  </div>
                                  <div className="ml-4">
                                    <div className={`w-2 h-2 rounded-full ${
                                      activity.action.includes('CREATE') ? 'bg-green-400' :
                                      activity.action.includes('UPDATE') ? 'bg-blue-400' :
                                      activity.action.includes('DELETE') ? 'bg-red-400' :
                                      'bg-gray-400'
                                    }`}></div>
                                  </div>
                                </div>
                              </div>
                            ))
                          ) : (
                            <div className="text-center py-4">
                              <p className="text-gray-500 text-sm">No recent activity</p>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Create User Form */}
                      <div className="bg-[#0a1628] rounded-lg p-5 border border-[#2d4a6f]">
                        <h3 className="text-sm font-medium text-white mb-4">Create New User</h3>
                        <form onSubmit={handleCreateUser} className="space-y-4">
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <div>
                              <label className="block text-xs text-gray-500 mb-2">Email Address</label>
                              <input
                                type="email"
                                value={newEmail}
                                onChange={(e) => setNewEmail(e.target.value)}
                                className="w-full px-3 py-2 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
                                placeholder="user@example.com"
                                required
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-2">Full Name</label>
                              <input
                                type="text"
                                value={newFullName}
                                onChange={(e) => setNewFullName(e.target.value)}
                                className="w-full px-3 py-2 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
                                placeholder="John Doe"
                              />
                            </div>
                          </div>
                          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                            <div>
                              <label className="block text-xs text-gray-500 mb-2">Phone Code</label>
                              <div className="relative">
                                <button
                                  type="button"
                                  onClick={() => setNewShowPhoneCodeDropdown(!newShowPhoneCodeDropdown)}
                                  className="w-full px-3 py-2 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white text-sm flex items-center justify-between"
                                >
                                  <span>{newSelectedPhoneCode ? newSelectedPhoneCode.phoneCode : 'Select'}</span>
                                  <ChevronDown className="h-4 w-4 text-gray-400" />
                                </button>
                                {newShowPhoneCodeDropdown && (
                                  <div className="absolute top-full left-0 right-0 z-50 bg-[#1e3a5f] border border-[#2d4a6f] rounded-b-lg max-h-48 overflow-y-auto">
                                    {countries.map((countryData) => (
                                      <button
                                        key={countryData.code}
                                        type="button"
                                        onClick={() => handleNewPhoneCodeSelect(countryData)}
                                        className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-[#2d4a6f]"
                                      >
                                        {countryData.name} {countryData.phoneCode}
                                      </button>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-2">Phone Number</label>
                              <input
                                type="tel"
                                value={newPhone}
                                onChange={e => setNewPhone(e.target.value)}
                                className="w-full px-3 py-2 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
                                placeholder="123-456-7890"
                              />
                            </div>
                            <div>
                              <label className="block text-xs text-gray-500 mb-2">Country</label>
                              <div className="relative">
                                <button
                                  type="button"
                                  onClick={() => setNewShowCountryDropdown(!newShowCountryDropdown)}
                                  className="w-full px-3 py-2 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white text-sm flex items-center justify-between"
                                >
                                  <span>{newSelectedCountry ? newSelectedCountry.name : 'Select'}</span>
                                </button>
                                {newShowCountryDropdown && (
                                  <div className="absolute top-full left-0 right-0 z-50 bg-[#1e3a5f] border border-[#2d4a6f] rounded-b-lg max-h-48 overflow-y-auto">
                                    {countries.map((countryData) => (
                                      <button
                                        key={countryData.code}
                                        type="button"
                                        onClick={() => handleNewCountrySelect(countryData)}
                                        className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-[#2d4a6f]"
                                      >
                                        {countryData.name}
                                      </button>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <div>
                              <label className="block text-xs text-gray-500 mb-2">Password</label>
                              <input
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                className="w-full px-3 py-2 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
                                placeholder="••••••••"
                                required
                              />
                            </div>
                            <div className="flex items-center">
                              <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={newIsAdmin}
                                  onChange={(e) => setNewIsAdmin(e.target.checked)}
                                  className="h-4 w-4 rounded border-[#2d4a6f] bg-[#1e3a5f] text-blue-500"
                                />
                                Admin privileges
                              </label>
                            </div>
                          </div>
                          <button
                            type="submit"
                            disabled={isCreating}
                            className="w-full bg-blue-600 text-white font-medium py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 text-sm"
                          >
                            {isCreating ? 'Creating...' : 'Create User'}
                          </button>
                        </form>
                      </div>
                    </div>
                  </div>
                )}

                {activeAdminTab === 'users' && (
                  <div className="space-y-4">
                    {/* Search and Filters */}
                    <div className="flex flex-col sm:flex-row gap-3">
                      <form onSubmit={handleSearch} className="flex-1 flex gap-2">
                        <input
                          type="text"
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          placeholder="Search users..."
                          className="flex-1 px-3 py-2 bg-[#0a1628] border border-[#2d4a6f] rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
                        />
                        <button type="submit" className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
                          Search
                        </button>
                      </form>
                      <div className="flex gap-2">
                        <button onClick={exportUsers} className="px-3 py-2 bg-[#0a1628] border border-[#2d4a6f] text-gray-400 rounded-lg text-sm hover:text-white">
                          Export
                        </button>
                        <button onClick={() => setShowBulkActions(!showBulkActions)} className={`px-3 py-2 border rounded-lg text-sm ${showBulkActions ? 'bg-blue-600 border-blue-500 text-white' : 'bg-[#0a1628] border-[#2d4a6f] text-gray-400 hover:text-white'}`}>
                          {showBulkActions ? '✕ Close Import' : '📥 Import Users'}
                        </button>
                      </div>
                    </div>

                    {/* Bulk Import Panel */}
                    {showBulkActions && (
                      <div className="mb-4">
                        <BulkUserImport />
                      </div>
                    )}

                    {/* User Type Filter Tabs */}
                    <div className="flex gap-1 bg-[#0a1628] p-1 rounded-lg border border-[#2d4a6f]">
                      <button
                        onClick={() => setUserTypeFilter('all')}
                        className={`flex-1 px-2 py-2 rounded text-xs transition-all ${
                          userTypeFilter === 'all' ? 'bg-[#1e3a5f] text-white' : 'text-gray-500 hover:text-white'
                        }`}
                      >
                        All ({users.length})
                      </button>
                      <button
                        onClick={() => setUserTypeFilter('journal')}
                        className={`flex-1 px-2 py-2 rounded text-xs transition-all ${
                          userTypeFilter === 'journal' ? 'bg-[#1e3a5f] text-white' : 'text-gray-500 hover:text-white'
                        }`}
                      >
                        Journal ({users.filter(u => u.has_journal_access).length})
                      </button>
                      <button
                        onClick={() => setUserTypeFilter('no-journal')}
                        className={`flex-1 px-2 py-2 rounded text-xs transition-all ${
                          userTypeFilter === 'no-journal' ? 'bg-[#1e3a5f] text-white' : 'text-gray-500 hover:text-white'
                        }`}
                      >
                        No Journal ({users.filter(u => !u.has_journal_access && u.user_source !== 'talaria-prop' && u.user_source !== 'hermes-website').length})
                      </button>
                      <button
                        onClick={() => setUserTypeFilter('mentorship')}
                        className={`flex-1 px-2 py-2 rounded text-xs transition-all ${
                          userTypeFilter === 'mentorship' ? 'bg-[#1e3a5f] text-white' : 'text-gray-500 hover:text-white'
                        }`}
                      >
                        Mentorship Applicant ({users.filter(u => bootcampEmails.includes(u.email?.toLowerCase())).length})
                      </button>
                      <button
                        onClick={() => setUserTypeFilter('talaria-prop')}
                        className={`flex-1 px-2 py-2 rounded text-xs transition-all ${
                          userTypeFilter === 'talaria-prop' ? 'bg-[#1e3a5f] text-white' : 'text-gray-500 hover:text-white'
                        }`}
                      >
                        Talaria-prop ({users.filter(u => u.user_source === 'talaria-prop').length})
                      </button>
                      <button
                        onClick={() => setUserTypeFilter('hermes-website')}
                        className={`flex-1 px-2 py-2 rounded text-xs transition-all ${
                          userTypeFilter === 'hermes-website' ? 'bg-[#1e3a5f] text-white' : 'text-gray-500 hover:text-white'
                        }`}
                      >
                        Hermes ({users.filter(u => u.user_source === 'hermes-website').length})
                      </button>
                      <button
                        onClick={() => setUserTypeFilter('duplicates')}
                        className={`flex-1 px-2 py-2 rounded text-xs transition-all ${
                          userTypeFilter === 'duplicates' ? 'bg-red-600 text-white' : 'text-red-400 hover:text-red-300'
                        }`}
                      >
                        Duplicates ({(() => {
                          const emailCounts = {};
                          users.forEach(u => { emailCounts[u.email?.toLowerCase()] = (emailCounts[u.email?.toLowerCase()] || 0) + 1; });
                          return users.filter(u => emailCounts[u.email?.toLowerCase()] > 1).length;
                        })()})
                      </button>
                    </div>

                    {/* Users List */}
                    {loadingUsers ? (
                      <div className="text-center py-8">
                        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-500 border-t-transparent mx-auto mb-4"></div>
                        <p className="text-gray-500 text-sm">Loading...</p>
                      </div>
                    ) : users.length === 0 ? (
                      <div className="text-center py-8">
                        <p className="text-gray-500 text-sm">No users found.</p>
                      </div>
                    ) : (
                      <div className="space-y-2 max-h-[600px] overflow-y-auto">
                        {users
                          .filter(user => {
                            if (userTypeFilter === 'journal') return user.has_journal_access;
                            if (userTypeFilter === 'no-journal') return !user.has_journal_access && user.user_source !== 'talaria-prop' && user.user_source !== 'hermes-website';
                            if (userTypeFilter === 'mentorship') return bootcampEmails.includes(user.email?.toLowerCase());
                            if (userTypeFilter === 'talaria-prop') return user.user_source === 'talaria-prop';
                            if (userTypeFilter === 'hermes-website') return user.user_source === 'hermes-website';
                            if (userTypeFilter === 'duplicates') {
                              const emailCounts = {};
                              users.forEach(u => { emailCounts[u.email?.toLowerCase()] = (emailCounts[u.email?.toLowerCase()] || 0) + 1; });
                              return emailCounts[user.email?.toLowerCase()] > 1;
                            }
                            return true;
                          })
                          .map(user => (
                          <div key={user.id} className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f] hover:border-blue-500/50 transition-all">
                            <div className="flex items-center justify-between gap-3">
                              <div className="flex items-center gap-3 flex-1 min-w-0">
                                <input
                                  type="checkbox"
                                  checked={selectedUsers.includes(user.id)}
                                  onChange={() => toggleUserSelection(user.id)}
                                  className="h-4 w-4 rounded border-[#2d4a6f] bg-[#1e3a5f] text-blue-500"
                                />
                                <div className="w-8 h-8 rounded-full bg-[#1e3a5f] flex items-center justify-center text-white text-sm font-medium">
                                  {(user.full_name || user.email).charAt(0).toUpperCase()}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap">
                                    <span className="text-sm font-medium text-white truncate">{user.full_name || 'No Name'}</span>
                                    {user.is_admin && <span className="text-xs text-yellow-400">Admin</span>}
                                    {user.has_journal_access ? (
                                      <span className="text-xs text-green-400">Journal user</span>
                                    ) : (
                                      <span className="text-xs text-purple-400">user</span>
                                    )}
                                  </div>
                                  <p className="text-xs text-gray-500 truncate">{user.email}</p>
                                </div>
                              </div>
                              <div className="hidden sm:flex items-center gap-3 shrink-0">
                                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#1e3a5f] border border-[#2d4a6f]" title="Trading journals">
                                  <BookOpen className="w-3.5 h-3.5 text-blue-400" />
                                  <span className="text-xs text-gray-300">{user.journals_count ?? user.profiles_count ?? 0}</span>
                                  <span className="text-xs text-gray-500">Journals</span>
                                </div>
                                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#1e3a5f] border border-[#2d4a6f]" title="Trades logged">
                                  <TrendingUp className="w-3.5 h-3.5 text-green-400" />
                                  <span className="text-xs text-gray-300">{user.trades_count ?? 0}</span>
                                  <span className="text-xs text-gray-500">Trades</span>
                                </div>
                              </div>
                              <div className="flex items-center gap-1 shrink-0">
                                <button
                                  onClick={() => loginAsUser(user.id)}
                                  className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-blue-400 hover:text-white hover:bg-blue-500/20 rounded-md border border-blue-500/30 transition-colors"
                                  title="Login as this user"
                                >
                                  <LogIn className="w-3.5 h-3.5" />
                                  <span className="hidden md:inline">Login</span>
                                </button>
                                <button onClick={() => handleEditUser(user)} className="p-2 text-gray-500 hover:text-blue-400" title="Edit">
                                  <Edit className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleDeleteUser(user.id)}
                                  disabled={isDeleting === user.id}
                                  className="p-2 text-gray-500 hover:text-red-400 disabled:opacity-50"
                                  title="Delete"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            </div>
                            <div className="flex sm:hidden items-center gap-3 mt-3 ml-11">
                              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#1e3a5f] border border-[#2d4a6f]">
                                <BookOpen className="w-3.5 h-3.5 text-blue-400" />
                                <span className="text-xs text-gray-300">{user.journals_count ?? user.profiles_count ?? 0}</span>
                                <span className="text-xs text-gray-500">Journals</span>
                              </div>
                              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-[#1e3a5f] border border-[#2d4a6f]">
                                <TrendingUp className="w-3.5 h-3.5 text-green-400" />
                                <span className="text-xs text-gray-300">{user.trades_count ?? 0}</span>
                                <span className="text-xs text-gray-500">Trades</span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Pagination */}
                    {pagination.total > pagination.per_page && (
                      <div className="flex items-center justify-between mt-4 text-sm">
                        <span className="text-gray-500">
                          {((pagination.page - 1) * pagination.per_page) + 1}-{Math.min(pagination.page * pagination.per_page, pagination.total)} of {pagination.total}
                        </span>
                        <div className="flex gap-1">
                          <button
                            onClick={() => handlePageChange(pagination.page - 1)}
                            disabled={pagination.page <= 1}
                            className="p-2 text-gray-500 hover:text-white disabled:opacity-50 rounded"
                          >
                            <ChevronLeft className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handlePageChange(pagination.page + 1)}
                            disabled={pagination.page >= Math.ceil(pagination.total / pagination.per_page)}
                            className="p-2 text-gray-500 hover:text-white disabled:opacity-50 rounded"
                          >
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Bulk Import Tab */}
                {activeAdminTab === 'bulk-import' && (
                  <div className="space-y-4">
                    <h3 className="text-sm font-medium text-white">Bulk User Import</h3>
                    <BulkUserImport />
                  </div>
                )}

                {/* Logs Tab */}
                {activeAdminTab === 'logs' && (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-medium text-white">Admin Logs</h3>
                      <button onClick={fetchLogs} className="text-gray-500 hover:text-white text-xs">Refresh</button>
                    </div>
                    <div className="max-h-96 overflow-y-auto space-y-2">
                      {logs.length === 0 ? (
                        <p className="text-gray-500 text-sm text-center py-8">No logs found.</p>
                      ) : (
                        logs.map((log, index) => (
                          <div key={index} className="bg-[#0a1628] rounded-lg p-3 border border-[#2d4a6f]">
                            <div className="text-sm text-white">{log.action}</div>
                            <div className="text-xs text-gray-500">{log.timestamp}</div>
                            {log.details && <div className="text-xs text-gray-400 mt-1">{log.details}</div>}
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}

                {/* System Health Tab */}
                {activeAdminTab === 'health' && (
                  <div className="space-y-6">
                    {/* Clean Header */}
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-2xl font-semibold text-white tracking-tight">System Health</h2>
                        <p className="text-sm text-gray-500 mt-1">
                          {serverMonitoring?.timestamp ? `Updated ${new Date(serverMonitoring.timestamp).toLocaleTimeString()}` : 'Real-time monitoring'}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setAutoRefresh(!autoRefresh)}
                          className={`h-9 px-3 rounded-lg text-xs font-medium transition-all ${
                            autoRefresh ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20' : 'bg-white/5 text-gray-400 ring-1 ring-white/10'
                          }`}
                        >
                          {autoRefresh ? 'Auto ON' : 'Auto OFF'}
                        </button>
                        <button
                          onClick={() => { fetchSystemHealth(); fetchServerMonitoring(); }}
                          disabled={serverMonitoringLoading}
                          className="h-9 px-4 bg-white text-gray-900 rounded-lg text-sm font-medium hover:bg-gray-100 transition-all disabled:opacity-50 flex items-center gap-2"
                        >
                          <RefreshCw className={`w-3.5 h-3.5 ${serverMonitoringLoading ? 'animate-spin' : ''}`} />
                          Refresh
                        </button>
                      </div>
                    </div>

                    {/* Status + Score Banner */}
                    {serverMonitoring && (
                      <div className={`rounded-xl p-5 flex items-center justify-between ${
                        serverMonitoring.health_status === 'healthy' ? 'bg-emerald-500/5 ring-1 ring-emerald-500/20' :
                        serverMonitoring.health_status === 'warning' ? 'bg-amber-500/5 ring-1 ring-amber-500/20' :
                        'bg-red-500/5 ring-1 ring-red-500/20'
                      }`}>
                        <div className="flex items-center gap-4">
                          <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${
                            serverMonitoring.health_status === 'healthy' ? 'bg-emerald-500/10' :
                            serverMonitoring.health_status === 'warning' ? 'bg-amber-500/10' : 'bg-red-500/10'
                          }`}>
                            {serverMonitoring.health_status === 'healthy' ? (
                              <CheckCircle className="w-6 h-6 text-emerald-400" />
                            ) : serverMonitoring.health_status === 'warning' ? (
                              <AlertTriangle className="w-6 h-6 text-amber-400" />
                            ) : (
                              <AlertCircle className="w-6 h-6 text-red-400" />
                            )}
                          </div>
                          <div>
                            <p className={`text-lg font-semibold ${
                              serverMonitoring.health_status === 'healthy' ? 'text-emerald-400' :
                              serverMonitoring.health_status === 'warning' ? 'text-amber-400' : 'text-red-400'
                            }`}>
                              {serverMonitoring.health_status === 'healthy' ? 'All Systems Operational' :
                               serverMonitoring.health_status === 'warning' ? 'Performance Degraded' : 'Issues Detected'}
                            </p>
                            <p className="text-sm text-gray-500">{serverMonitoring.issues?.length || 0} issues · {serverMonitoring.warnings?.length || 0} warnings</p>
                          </div>
                        </div>
                        {serverMonitoring.security_score && (
                          <div className="flex items-center gap-4">
                            <div className="text-right hidden sm:block">
                              <p className="text-xs text-gray-500 uppercase tracking-wide">Security</p>
                              <p className="text-xl font-bold text-white">{serverMonitoring.security_score.score}/100</p>
                            </div>
                            <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-2xl font-black ${
                              serverMonitoring.security_score.grade === 'A' ? 'bg-emerald-500 text-white' :
                              serverMonitoring.security_score.grade === 'B' ? 'bg-blue-500 text-white' :
                              serverMonitoring.security_score.grade === 'C' ? 'bg-amber-500 text-white' :
                              'bg-red-500 text-white'
                            }`}>{serverMonitoring.security_score.grade}</div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Metrics Cards */}
                    <div className="grid grid-cols-4 gap-4">
                      <div className="bg-[#0d1829] rounded-xl p-5 ring-1 ring-white/5">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs text-gray-500 uppercase tracking-wide">CPU</span>
                          <Cpu className="w-4 h-4 text-gray-600" />
                        </div>
                        <p className="text-3xl font-semibold text-white">{serverMonitoring?.system?.cpu?.percent?.toFixed(0) || 0}<span className="text-lg text-gray-500">%</span></p>
                        <div className="mt-3 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${(serverMonitoring?.system?.cpu?.percent || 0) > 80 ? 'bg-red-500' : (serverMonitoring?.system?.cpu?.percent || 0) > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{width: `${serverMonitoring?.system?.cpu?.percent || 0}%`}} />
                        </div>
                      </div>
                      <div className="bg-[#0d1829] rounded-xl p-5 ring-1 ring-white/5">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs text-gray-500 uppercase tracking-wide">Memory</span>
                          <HardDrive className="w-4 h-4 text-gray-600" />
                        </div>
                        <p className="text-3xl font-semibold text-white">{serverMonitoring?.system?.memory?.percent?.toFixed(0) || 0}<span className="text-lg text-gray-500">%</span></p>
                        <div className="mt-3 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${(serverMonitoring?.system?.memory?.percent || 0) > 80 ? 'bg-red-500' : (serverMonitoring?.system?.memory?.percent || 0) > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{width: `${serverMonitoring?.system?.memory?.percent || 0}%`}} />
                        </div>
                        <p className="text-xs text-gray-600 mt-2">{serverMonitoring?.system?.memory?.used_mb || 0} / {serverMonitoring?.system?.memory?.total_mb || 0} MB</p>
                      </div>
                      <div className="bg-[#0d1829] rounded-xl p-5 ring-1 ring-white/5">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs text-gray-500 uppercase tracking-wide">Disk</span>
                          <Database className="w-4 h-4 text-gray-600" />
                        </div>
                        <p className="text-3xl font-semibold text-white">{parseInt(serverMonitoring?.system?.disk?.percent) || 0}<span className="text-lg text-gray-500">%</span></p>
                        <div className="mt-3 h-1.5 bg-gray-800 rounded-full overflow-hidden">
                          <div className={`h-full rounded-full transition-all ${(parseInt(serverMonitoring?.system?.disk?.percent) || 0) > 80 ? 'bg-red-500' : (parseInt(serverMonitoring?.system?.disk?.percent) || 0) > 60 ? 'bg-amber-500' : 'bg-emerald-500'}`} style={{width: `${parseInt(serverMonitoring?.system?.disk?.percent) || 0}%`}} />
                        </div>
                        <p className="text-xs text-gray-600 mt-2">{serverMonitoring?.system?.disk?.used || '0'} / {serverMonitoring?.system?.disk?.total || '0'}</p>
                      </div>
                      <div className="bg-[#0d1829] rounded-xl p-5 ring-1 ring-white/5">
                        <div className="flex items-center justify-between mb-3">
                          <span className="text-xs text-gray-500 uppercase tracking-wide">Uptime</span>
                          <Clock className="w-4 h-4 text-gray-600" />
                        </div>
                        <p className="text-lg font-semibold text-white">{serverMonitoring?.system?.uptime || 'N/A'}</p>
                        <p className="text-xs text-gray-600 mt-2">Load: {serverMonitoring?.system?.load_average || 'N/A'}</p>
                      </div>
                    </div>

                    {/* Sub-tabs Navigation */}
                    <div className="flex gap-1 bg-[#0a1628] p-1 rounded-lg border border-[#2d4a6f]">
                      {[
                        { id: 'overview', label: '📊 Overview', icon: Activity },
                        { id: 'security', label: '🛡️ Security', icon: Shield },
                        { id: 'services', label: '🐳 Services', icon: Server },
                        { id: 'attackmap', label: '🗺️ Attack Map', icon: Globe },
                        { id: 'intrusion', label: '🔍 Intrusion', icon: Shield }
                      ].map(tab => (
                        <button
                          key={tab.id}
                          onClick={() => setHealthSubTab(tab.id)}
                          className={`flex-1 px-3 py-2 rounded text-sm font-medium transition-all ${
                            healthSubTab === tab.id ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white hover:bg-[#1e3a5f]'
                          }`}
                        >
                          {tab.label}
                        </button>
                      ))}
                    </div>

                    {/* Security Score Card */}
                    {serverMonitoring?.security_score && (
                      <div className="bg-gradient-to-br from-[#0a1628] to-[#1e3a5f] rounded-xl p-5 border border-[#2d4a6f]">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-6">
                            <div className={`relative w-20 h-20 rounded-full flex items-center justify-center border-4 ${
                              serverMonitoring.security_score.grade === 'A' ? 'bg-green-500/20 border-green-500' :
                              serverMonitoring.security_score.grade === 'B' ? 'bg-blue-500/20 border-blue-500' :
                              serverMonitoring.security_score.grade === 'C' ? 'bg-yellow-500/20 border-yellow-500' :
                              serverMonitoring.security_score.grade === 'D' ? 'bg-orange-500/20 border-orange-500' :
                              'bg-red-500/20 border-red-500'
                            }`}>
                              <div className="text-center">
                                <span className={`text-3xl font-black ${
                                  serverMonitoring.security_score.grade === 'A' ? 'text-green-400' :
                                  serverMonitoring.security_score.grade === 'B' ? 'text-blue-400' :
                                  serverMonitoring.security_score.grade === 'C' ? 'text-yellow-400' :
                                  serverMonitoring.security_score.grade === 'D' ? 'text-orange-400' :
                                  'text-red-400'
                                }`}>{serverMonitoring.security_score.grade}</span>
                              </div>
                            </div>
                            <div>
                              <h4 className="text-lg font-bold text-white">Security Score</h4>
                              <p className="text-2xl font-bold text-gray-300">{serverMonitoring.security_score.score}/100</p>
                            </div>
                          </div>
                          <div className="flex-1 max-w-sm ml-6 space-y-1">
                            {serverMonitoring.security_score.factors?.slice(0, 3).map((f, idx) => (
                              <div key={idx} className={`flex items-center justify-between text-xs px-2 py-1 rounded ${
                                f.type === 'positive' ? 'bg-green-500/10 text-green-400' :
                                f.type === 'warning' ? 'bg-yellow-500/10 text-yellow-400' :
                                'bg-red-500/10 text-red-400'
                              }`}>
                                <span className="truncate">{f.factor}</span>
                                <span className="font-bold ml-2">{f.impact > 0 ? '+' : ''}{f.impact}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Attack Map Tab */}
                    {healthSubTab === 'attackmap' && serverMonitoring?.security?.ssh_attacks?.top_attackers && (
                      <div className="bg-[#0a1628] rounded-xl p-5 border border-[#2d4a6f]">
                        <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                          <Globe className="w-4 h-4 text-red-400" />
                          Live Attack Origins
                        </h4>
                        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                          {serverMonitoring.security.ssh_attacks.top_attackers.map((attacker, idx) => (
                            <div key={idx} className="bg-[#1e3a5f]/50 rounded-lg p-3 border border-red-500/20 hover:border-red-500/50 transition-all">
                              <div className="flex items-center gap-2 mb-2">
                                {attacker.country_code && (
                                  <img src={`https://flagcdn.com/20x15/${attacker.country_code.toLowerCase()}.png`} alt="" className="w-5 h-4" onError={(e) => e.target.style.display = 'none'} />
                                )}
                                <span className="text-white font-medium text-sm">{attacker.country || 'Unknown'}</span>
                                <span className="ml-auto text-red-400 font-bold">{attacker.count}</span>
                              </div>
                              <div className="flex items-center justify-between">
                                <span className="text-xs text-gray-400 font-mono">{attacker.ip}</span>
                                <button
                                  onClick={async () => {
                                    if (window.confirm(`Block ${attacker.ip}?`)) {
                                      const res = await fetch(`${API_BASE_URL}/admin/monitoring/block-ip?ip=${attacker.ip}`, {
                                        method: 'POST', headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                                      });
                                      const data = await res.json();
                                      alert(data.success ? 'Blocked!' : data.error);
                                      fetchServerMonitoring();
                                    }
                                  }}
                                  className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/40"
                                >Block</button>
                              </div>
                            </div>
                          ))}
                        </div>
                        <div className="grid grid-cols-3 gap-4 mt-4">
                          <div className="bg-red-500/10 rounded-lg p-3 text-center border border-red-500/30">
                            <p className="text-2xl font-bold text-red-400">{serverMonitoring.security.ssh_attacks.total_failed_attempts || 0}</p>
                            <p className="text-xs text-gray-400">SSH Attacks</p>
                          </div>
                          <div className="bg-yellow-500/10 rounded-lg p-3 text-center border border-yellow-500/30">
                            <p className="text-2xl font-bold text-yellow-400">{serverMonitoring.security.web_attacks?.suspicious_requests || 0}</p>
                            <p className="text-xs text-gray-400">Web Attacks</p>
                          </div>
                          <div className="bg-green-500/10 rounded-lg p-3 text-center border border-green-500/30">
                            <p className="text-2xl font-bold text-green-400">{serverMonitoring.security.fail2ban?.banned_count || 0}</p>
                            <p className="text-xs text-gray-400">Blocked</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Overview Tab - Health Status */}
                    {healthSubTab === 'overview' && serverMonitoring && (
                      <div className={`rounded-lg p-4 border ${
                        serverMonitoring.health_status === 'healthy' ? 'bg-green-500/10 border-green-500/30' :
                        serverMonitoring.health_status === 'warning' ? 'bg-yellow-500/10 border-yellow-500/30' :
                        'bg-red-500/10 border-red-500/30'
                      }`}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className={`w-3 h-3 rounded-full ${
                              serverMonitoring.health_status === 'healthy' ? 'bg-green-500' :
                              serverMonitoring.health_status === 'warning' ? 'bg-yellow-500' : 'bg-red-500'
                            }`} />
                            <div>
                              <p className="text-lg font-bold text-white capitalize">{serverMonitoring.health_status}</p>
                              <p className="text-xs text-gray-500">Updated: {new Date(serverMonitoring.timestamp).toLocaleTimeString()}</p>
                            </div>
                          </div>
                          {(serverMonitoring.issues?.length > 0 || serverMonitoring.warnings?.length > 0) && (
                            <div className="text-right">
                              {serverMonitoring.issues?.length > 0 && (
                                <>
                                  <p className="text-sm font-semibold text-red-400">{serverMonitoring.issues.length} Issue(s)</p>
                                  {serverMonitoring.issues.map((issue, idx) => (
                                    <p key={idx} className="text-xs text-red-400">{issue}</p>
                                  ))}
                                </>
                              )}
                              {serverMonitoring.warnings?.length > 0 && (
                                <>
                                  <p className="text-sm font-semibold text-yellow-400">{serverMonitoring.warnings.length} Warning(s)</p>
                                  {serverMonitoring.warnings.map((warning, idx) => (
                                    <p key={idx} className="text-xs text-yellow-400">{warning}</p>
                                  ))}
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    )}

                    {/* System Resources with Circular Gauges */}
                    {serverMonitoring?.system && (
                      <div className="bg-[#0a1628] rounded-lg p-5 border border-[#2d4a6f]">
                        <h4 className="text-sm font-medium text-white mb-4">System Resources</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                          {/* CPU Gauge */}
                          <div className="bg-[#1e3a5f] rounded-xl p-5 flex flex-col items-center">
                            <div className="relative w-32 h-32">
                              <svg className="w-32 h-32 transform -rotate-90">
                                <circle cx="64" cy="64" r="56" stroke="#0a1628" strokeWidth="12" fill="none" />
                                <circle 
                                  cx="64" cy="64" r="56" 
                                  stroke={serverMonitoring.system.cpu?.percent > 90 ? '#ef4444' : serverMonitoring.system.cpu?.percent > 70 ? '#eab308' : '#22c55e'}
                                  strokeWidth="12" 
                                  fill="none"
                                  strokeLinecap="round"
                                  strokeDasharray={`${(serverMonitoring.system.cpu?.percent || 0) * 3.52} 352`}
                                  className="transition-all duration-500"
                                />
                              </svg>
                              <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <Cpu className="w-5 h-5 text-blue-400 mb-1" />
                                <span className="text-2xl font-bold text-white">{serverMonitoring.system.cpu?.percent?.toFixed(0) || 0}%</span>
                              </div>
                            </div>
                            <span className="text-sm font-medium text-white mt-3">CPU Usage</span>
                            <span className={`text-xs px-2 py-1 rounded mt-1 ${
                              serverMonitoring.system.cpu?.status === 'ok' ? 'bg-green-500/20 text-green-400' :
                              serverMonitoring.system.cpu?.status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>{serverMonitoring.system.cpu?.status}</span>
                          </div>

                          {/* Memory Gauge */}
                          <div className="bg-[#1e3a5f] rounded-xl p-5 flex flex-col items-center">
                            <div className="relative w-32 h-32">
                              <svg className="w-32 h-32 transform -rotate-90">
                                <circle cx="64" cy="64" r="56" stroke="#0a1628" strokeWidth="12" fill="none" />
                                <circle 
                                  cx="64" cy="64" r="56" 
                                  stroke={serverMonitoring.system.memory?.percent > 90 ? '#ef4444' : serverMonitoring.system.memory?.percent > 70 ? '#eab308' : '#22c55e'}
                                  strokeWidth="12" 
                                  fill="none"
                                  strokeLinecap="round"
                                  strokeDasharray={`${(serverMonitoring.system.memory?.percent || 0) * 3.52} 352`}
                                  className="transition-all duration-500"
                                />
                              </svg>
                              <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <HardDrive className="w-5 h-5 text-purple-400 mb-1" />
                                <span className="text-2xl font-bold text-white">{serverMonitoring.system.memory?.percent?.toFixed(0) || 0}%</span>
                              </div>
                            </div>
                            <span className="text-sm font-medium text-white mt-3">Memory</span>
                            <span className="text-xs text-gray-400">{serverMonitoring.system.memory?.used_mb || 0} / {serverMonitoring.system.memory?.total_mb || 0} MB</span>
                            <span className={`text-xs px-2 py-1 rounded mt-1 ${
                              serverMonitoring.system.memory?.status === 'ok' ? 'bg-green-500/20 text-green-400' :
                              serverMonitoring.system.memory?.status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>{serverMonitoring.system.memory?.status}</span>
                          </div>

                          {/* Disk Gauge */}
                          <div className="bg-[#1e3a5f] rounded-xl p-5 flex flex-col items-center">
                            <div className="relative w-32 h-32">
                              <svg className="w-32 h-32 transform -rotate-90">
                                <circle cx="64" cy="64" r="56" stroke="#0a1628" strokeWidth="12" fill="none" />
                                <circle 
                                  cx="64" cy="64" r="56" 
                                  stroke={parseInt(serverMonitoring.system.disk?.percent) > 90 ? '#ef4444' : parseInt(serverMonitoring.system.disk?.percent) > 70 ? '#eab308' : '#22c55e'}
                                  strokeWidth="12" 
                                  fill="none"
                                  strokeLinecap="round"
                                  strokeDasharray={`${(parseInt(serverMonitoring.system.disk?.percent) || 0) * 3.52} 352`}
                                  className="transition-all duration-500"
                                />
                              </svg>
                              <div className="absolute inset-0 flex flex-col items-center justify-center">
                                <Database className="w-5 h-5 text-cyan-400 mb-1" />
                                <span className="text-2xl font-bold text-white">{parseInt(serverMonitoring.system.disk?.percent) || 0}%</span>
                              </div>
                            </div>
                            <span className="text-sm font-medium text-white mt-3">Disk Storage</span>
                            <span className="text-xs text-gray-400">{serverMonitoring.system.disk?.used || '0'} / {serverMonitoring.system.disk?.total || '0'}</span>
                            <span className={`text-xs px-2 py-1 rounded mt-1 ${
                              serverMonitoring.system.disk?.status === 'ok' ? 'bg-green-500/20 text-green-400' :
                              serverMonitoring.system.disk?.status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                              'bg-red-500/20 text-red-400'
                            }`}>{serverMonitoring.system.disk?.status}</span>
                          </div>
                        </div>

                        {/* Uptime & Load Average Cards */}
                        <div className="grid grid-cols-2 gap-4 mt-4">
                          <div className="bg-[#1e3a5f] rounded-lg p-4">
                            <span className="text-xs text-gray-400">Uptime</span>
                            <p className="text-lg font-bold text-white mt-1">{serverMonitoring.system.uptime || 'N/A'}</p>
                          </div>
                          <div className="bg-[#1e3a5f] rounded-lg p-4">
                            <span className="text-xs text-gray-400">Load Average</span>
                            <p className="text-lg font-bold text-white mt-1">{serverMonitoring.system.load_average || 'N/A'}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Security & Threat Protection */}
                    <div className="bg-[#0a1628] rounded-lg p-5 border border-[#2d4a6f]">
                      <div className="flex items-center justify-between mb-4">
                        <h4 className="text-sm font-medium text-white flex items-center gap-2">
                          <Shield className="w-4 h-4 text-blue-400" />
                          Security & Threat Protection
                        </h4>
                        <button
                          onClick={fetchSecurityData}
                          className="text-xs px-2 py-1 rounded bg-blue-500/20 text-blue-400 hover:bg-blue-500/30"
                        >
                          Load Security Data
                        </button>
                      </div>

                      {/* Security Stats */}
                      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                        <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <div className="w-2 h-2 rounded-full bg-green-500" />
                            <span className="text-xs text-gray-400">Protection</span>
                          </div>
                          <p className="text-lg font-bold text-green-400">{securityStats?.protection_status || 'Active'}</p>
                        </div>
                        <div className={`rounded-lg p-4 border ${(securityStats?.blocked_ips_active || 0) > 0 ? 'bg-red-500/10 border-red-500/30' : 'bg-[#1e3a5f] border-[#2d4a6f]'}`}>
                          <div className="flex items-center gap-2 mb-2">
                            <Ban className="w-3 h-3 text-red-400" />
                            <span className="text-xs text-gray-400">Blocked IPs</span>
                          </div>
                          <p className="text-lg font-bold text-white">{securityStats?.blocked_ips_active || 0}</p>
                        </div>
                        <div className={`rounded-lg p-4 border ${(securityStats?.failed_logins_24h || 0) > 50 ? 'bg-red-500/10 border-red-500/30' : (securityStats?.failed_logins_24h || 0) > 10 ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-[#1e3a5f] border-[#2d4a6f]'}`}>
                          <div className="flex items-center gap-2 mb-2">
                            <AlertTriangle className="w-3 h-3 text-yellow-400" />
                            <span className="text-xs text-gray-400">Failed Logins (24h)</span>
                          </div>
                          <p className="text-lg font-bold text-white">{securityStats?.failed_logins_24h || 0}</p>
                        </div>
                        <div className="bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg p-4">
                          <div className="flex items-center gap-2 mb-2">
                            <Globe className="w-3 h-3 text-gray-400" />
                            <span className="text-xs text-gray-400">Threat IPs (24h)</span>
                          </div>
                          <p className="text-lg font-bold text-white">{securityStats?.unique_threat_ips || 0}</p>
                        </div>
                      </div>

                      {/* VPS Security Data (loads automatically with server monitoring) */}
                      {serverMonitoring?.security && (
                        <div className="mb-4">
                          <h5 className="text-xs font-medium text-gray-400 mb-3 flex items-center gap-2">
                            <Server className="w-3 h-3" />
                            VPS Security (Real-time from host logs)
                          </h5>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                            <div className={`rounded-lg p-4 border ${(serverMonitoring.security?.ssh_attacks?.total_failed_attempts || 0) > 100 ? 'bg-red-500/10 border-red-500/30' : 'bg-[#1e3a5f] border-[#2d4a6f]'}`}>
                              <div className="flex items-center gap-2 mb-2">
                                <AlertTriangle className="w-3 h-3 text-red-400" />
                                <span className="text-xs text-gray-400">SSH Brute Force Attempts</span>
                              </div>
                              <p className={`text-2xl font-bold ${(serverMonitoring.security?.ssh_attacks?.total_failed_attempts || 0) > 100 ? 'text-red-400' : 'text-white'}`}>
                                {serverMonitoring.security?.ssh_attacks?.total_failed_attempts || 0}
                              </p>
                            </div>
                            <div className={`rounded-lg p-4 border ${(serverMonitoring.security?.web_attacks?.suspicious_requests || 0) > 50 ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-[#1e3a5f] border-[#2d4a6f]'}`}>
                              <div className="flex items-center gap-2 mb-2">
                                <Globe className="w-3 h-3 text-yellow-400" />
                                <span className="text-xs text-gray-400">Suspicious Web Requests</span>
                              </div>
                              <p className={`text-2xl font-bold ${(serverMonitoring.security?.web_attacks?.suspicious_requests || 0) > 50 ? 'text-yellow-400' : 'text-white'}`}>
                                {serverMonitoring.security?.web_attacks?.suspicious_requests || 0}
                              </p>
                            </div>
                            <div className="bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg p-4">
                              <div className="flex items-center gap-2 mb-2">
                                <Shield className="w-3 h-3 text-green-400" />
                                <span className="text-xs text-gray-400">Fail2Ban Banned</span>
                              </div>
                              <p className="text-2xl font-bold text-white">{serverMonitoring.security?.fail2ban?.banned_count || 0}</p>
                            </div>
                          </div>

                          {/* Top Attackers */}
                          {serverMonitoring.security?.ssh_attacks?.top_attackers?.length > 0 && (
                            <div className="bg-[#1e3a5f] rounded-lg p-4">
                              <h6 className="text-xs font-medium text-gray-400 mb-3">Top Attacking IPs</h6>
                              <div className="space-y-2">
                                {serverMonitoring.security.ssh_attacks.top_attackers.map((attacker, idx) => (
                                  <div key={idx} className="flex items-center justify-between text-sm py-2 px-2 bg-[#0a1628]/50 rounded mb-1">
                                    <div className="flex items-center gap-2">
                                      {attacker.country_code && (
                                        <img 
                                          src={`https://flagcdn.com/16x12/${attacker.country_code.toLowerCase()}.png`}
                                          alt={attacker.country_code}
                                          className="w-4 h-3"
                                          onError={(e) => e.target.style.display = 'none'}
                                        />
                                      )}
                                      <span className="text-white font-mono text-xs">{attacker.ip}</span>
                                      <span className="text-gray-500 text-xs">{attacker.country || ''}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                      <span className={`text-xs font-bold px-2 py-0.5 rounded ${attacker.count > 50 ? 'bg-red-500/30 text-red-400' : attacker.count > 20 ? 'bg-yellow-500/30 text-yellow-400' : 'bg-gray-500/30 text-gray-300'}`}>
                                        {attacker.count}
                                      </span>
                                      <button
                                        onClick={async () => {
                                          if (window.confirm(`Block IP ${attacker.ip} from ${attacker.country || 'Unknown'}?`)) {
                                            try {
                                              const res = await fetch(`${API_BASE_URL}/admin/monitoring/block-ip?ip=${attacker.ip}`, {
                                                method: 'POST',
                                                headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
                                              });
                                              const data = await res.json();
                                              if (data.success) {
                                                alert(`✅ ${attacker.ip} blocked successfully!`);
                                                fetchServerMonitoring();
                                              } else {
                                                alert(`❌ Failed: ${data.error}`);
                                              }
                                            } catch (e) {
                                              alert(`❌ Error: ${e.message}`);
                                            }
                                          }
                                        }}
                                        className="px-2 py-1 bg-red-500/20 text-red-400 rounded text-xs hover:bg-red-500/40 transition-colors"
                                        title="Block this IP"
                                      >
                                        🚫 Block
                                      </button>
                                    </div>
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Block IP Form */}
                      <div className="bg-[#1e3a5f] rounded-lg p-4 mb-4">
                        <h5 className="text-xs font-medium text-gray-400 mb-3">Block IP Address</h5>
                        <div className="flex gap-2 flex-wrap">
                          <input
                            type="text"
                            value={newBlockIP}
                            onChange={(e) => setNewBlockIP(e.target.value)}
                            placeholder="IP Address"
                            className="flex-1 min-w-[150px] px-3 py-2 bg-[#0a1628] border border-[#2d4a6f] rounded text-white text-sm"
                          />
                          <input
                            type="text"
                            value={newBlockReason}
                            onChange={(e) => setNewBlockReason(e.target.value)}
                            placeholder="Reason (optional)"
                            className="flex-1 min-w-[150px] px-3 py-2 bg-[#0a1628] border border-[#2d4a6f] rounded text-white text-sm"
                          />
                          <button
                            onClick={handleBlockIP}
                            disabled={blockingIP || !newBlockIP.trim()}
                            className="px-4 py-2 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
                          >
                            {blockingIP ? 'Blocking...' : 'Block IP'}
                          </button>
                        </div>
                      </div>

                      {/* Blocked IPs Table */}
                      {blockedIPs.length > 0 && (
                        <div className="mb-4">
                          <h5 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-2">
                            <Ban className="w-3 h-3" />
                            Blocked IP Addresses ({blockedIPs.length})
                          </h5>
                          <div className="bg-[#1e3a5f] rounded-lg overflow-hidden">
                            <table className="w-full text-sm">
                              <thead>
                                <tr className="border-b border-[#2d4a6f]">
                                  <th className="text-left py-2 px-3 text-xs text-gray-400 font-medium">IP</th>
                                  <th className="text-left py-2 px-3 text-xs text-gray-400 font-medium">Reason</th>
                                  <th className="text-left py-2 px-3 text-xs text-gray-400 font-medium">Action</th>
                                </tr>
                              </thead>
                              <tbody>
                                {blockedIPs.slice(0, 10).map((item) => (
                                  <tr key={item.id} className="border-b border-[#2d4a6f]/50 last:border-0">
                                    <td className="py-2 px-3"><span className="text-red-400 font-mono text-xs">{item.ip_address}</span></td>
                                    <td className="py-2 px-3"><span className="text-xs text-gray-400">{item.reason}</span></td>
                                    <td className="py-2 px-3">
                                      <button onClick={() => handleUnblockIP(item.id)} className="text-xs text-blue-400 hover:text-blue-300">Unblock</button>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      )}

                      {/* Failed Logins */}
                      {serverMonitoring?.security?.recent_failed_ssh?.length > 0 && (
                        <div className="mt-4">
                          <h5 className="text-xs font-medium text-gray-400 mb-2 flex items-center gap-2">
                            <AlertCircle className="w-3 h-3 text-yellow-400" />
                            Recent Failed SSH Attempts
                          </h5>
                          <div className="bg-[#1e3a5f] rounded-lg p-3 font-mono text-xs text-yellow-400 max-h-32 overflow-y-auto space-y-1">
                            {serverMonitoring.security.recent_failed_ssh.map((attempt, idx) => (
                              <div key={idx} className="flex items-center gap-2">
                                <span className="text-gray-500">•</span>
                                <span>{attempt}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Services Status */}
                    {serverMonitoring?.services && (
                      <div className="bg-[#0a1628] rounded-lg p-5 border border-[#2d4a6f]">
                        <h4 className="text-sm font-medium text-white mb-4">Services Status</h4>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                          {serverMonitoring.services.services?.map((service, idx) => (
                            <div key={idx} className={`rounded-lg p-3 border text-center ${
                              service.ok ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'
                            }`}>
                              <div className={`w-2 h-2 rounded-full mx-auto mb-2 ${service.ok ? 'bg-green-500' : 'bg-red-500'}`} />
                              <p className="font-medium text-white capitalize text-sm">{service.name}</p>
                              <p className={`text-xs ${service.ok ? 'text-green-400' : 'text-red-400'}`}>{service.status}</p>
                            </div>
                          ))}
                        </div>

                        {/* Docker Containers */}
                        {serverMonitoring.services.docker_containers?.length > 0 && (
                          <div className="mt-4">
                            <h5 className="text-xs font-medium text-gray-400 mb-2">Docker Containers</h5>
                            <div className="bg-[#1e3a5f] rounded-lg p-3 font-mono text-xs text-green-400 max-h-32 overflow-y-auto">
                              {serverMonitoring.services.docker_containers.map((container, idx) => (
                                <div key={idx} className="flex items-center gap-2">
                                  <span className="text-green-500">●</span>
                                  <span>{container}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Application Health */}
                    {systemHealth && (
                      <div className="bg-[#0a1628] rounded-lg p-5 border border-[#2d4a6f]">
                        <h4 className="text-sm font-medium text-white mb-4">Application Health</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                          <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                            <span className="text-xs text-gray-400">API Status</span>
                            <p className="text-lg font-bold text-green-400 mt-1">{systemHealth.status || 'healthy'}</p>
                          </div>
                          <div className="bg-[#1e3a5f] rounded-lg p-4">
                            <span className="text-xs text-gray-400">App Uptime</span>
                            <p className="text-lg font-bold text-white mt-1">{systemHealth.uptime || 'N/A'}</p>
                          </div>
                          {systemHealth.database && (
                            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                              <span className="text-xs text-gray-400">Database</span>
                              <p className="text-lg font-bold text-green-400 mt-1">{systemHealth.database.status || 'healthy'}</p>
                            </div>
                          )}
                        </div>
                      </div>
                    )}


                    {/* Intrusion Detection Tab */}
                    {healthSubTab === 'intrusion' && (
                      <div className="space-y-6">
                        {!intrusionData && !securityAudit ? (
                          <div className="text-center py-8">
                            <button onClick={fetchIntrusionDetection} disabled={intrusionLoading} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 mx-auto">
                              {intrusionLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
                              {intrusionLoading ? 'Scanning...' : 'Run Security Scan'}
                            </button>
                            <p className="text-gray-500 text-sm mt-2">Scan for signs of intrusion or compromise</p>
                          </div>
                        ) : (
                          <React.Fragment>
                            {intrusionData && (
                              <div className={`rounded-xl p-5 flex items-center justify-between ${intrusionData.risk_level === 'low' ? 'bg-emerald-500/10 ring-1 ring-emerald-500/20' : intrusionData.risk_level === 'medium' ? 'bg-amber-500/10 ring-1 ring-amber-500/20' : 'bg-red-500/10 ring-1 ring-red-500/20'}`}>
                                <div className="flex items-center gap-4">
                                  <Shield className={`w-8 h-8 ${intrusionData.risk_level === 'low' ? 'text-emerald-400' : intrusionData.risk_level === 'medium' ? 'text-amber-400' : 'text-red-400'}`} />
                                  <div>
                                    <p className={`text-lg font-semibold ${intrusionData.risk_level === 'low' ? 'text-emerald-400' : intrusionData.risk_level === 'medium' ? 'text-amber-400' : 'text-red-400'}`}>
                                      {intrusionData.risk_level === 'low' ? 'No Threats Detected' : intrusionData.risk_level === 'medium' ? 'Potential Issues' : 'Critical Alerts!'}
                                    </p>
                                    <p className="text-sm text-gray-500">{intrusionData.alerts?.length || 0} alerts · {intrusionData.checks_performed?.length || 0} checks</p>
                                  </div>
                                </div>
                                <button onClick={fetchIntrusionDetection} disabled={intrusionLoading} className="px-4 py-2 bg-white/10 text-white rounded-lg hover:bg-white/20">
                                  <RefreshCw className={`w-4 h-4 ${intrusionLoading ? 'animate-spin' : ''}`} />
                                </button>
                              </div>
                            )}
                            {intrusionData?.alerts?.length > 0 && (
                              <div className="bg-[#0a1628] rounded-xl p-5 border border-red-500/30">
                                <h4 className="text-sm font-medium text-red-400 mb-4">Security Alerts ({intrusionData.alerts.length})</h4>
                                <div className="space-y-3">
                                  {intrusionData.alerts.map((alert, idx) => (
                                    <div key={idx} className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                                      <p className="font-medium text-red-400">{alert.message}</p>
                                      <p className="text-xs text-gray-500 mt-1">Severity: {alert.severity}</p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                            {securityAudit && (
                              <div className="bg-[#0a1628] rounded-xl p-5 border border-[#2d4a6f]">
                                <div className="flex items-center justify-between mb-4">
                                  <h4 className="text-sm font-medium text-white">Security Audit</h4>
                                  <span className={`px-3 py-1 rounded-lg font-bold ${securityAudit.grade === 'A' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                                    {securityAudit.grade} ({securityAudit.score}/100)
                                  </span>
                                </div>
                                <div className="grid grid-cols-3 gap-4 mb-4">
                                  <div className="bg-emerald-500/10 rounded-lg p-3 text-center">
                                    <p className="text-2xl font-bold text-emerald-400">{securityAudit.passed}</p>
                                    <p className="text-xs text-gray-400">Passed</p>
                                  </div>
                                  <div className="bg-amber-500/10 rounded-lg p-3 text-center">
                                    <p className="text-2xl font-bold text-amber-400">{securityAudit.warnings}</p>
                                    <p className="text-xs text-gray-400">Warnings</p>
                                  </div>
                                  <div className="bg-red-500/10 rounded-lg p-3 text-center">
                                    <p className="text-2xl font-bold text-red-400">{securityAudit.failed}</p>
                                    <p className="text-xs text-gray-400">Failed</p>
                                  </div>
                                </div>
                                <div className="space-y-2">
                                  {securityAudit.checks?.map((check, idx) => (
                                    <div key={idx} className={`flex items-center justify-between p-3 rounded-lg ${check.status === 'pass' ? 'bg-emerald-500/5' : 'bg-red-500/5'}`}>
                                      <span className="text-sm text-white">{check.name}</span>
                                      <span className={`text-xs ${check.status === 'pass' ? 'text-emerald-400' : 'text-red-400'}`}>{check.status}</span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                          </React.Fragment>
                        )}
                      </div>
                    )}
                    {/* Loading/Empty State */}
                    {!serverMonitoring && !systemHealth && (
                      <div className="text-center py-16">
                        <Server className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-500">Click Refresh to load server monitoring data</p>
                      </div>
                    )}
                  </div>
                )}

                {/* Analytics Tab */}
                {activeAdminTab === 'analytics' && (
                  <div className="space-y-6">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <h3 className="text-lg font-bold text-white">Analytics Dashboard</h3>
                      <button
                        onClick={fetchAnalytics}
                        disabled={analyticsLoading}
                        className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
                      >
                        <RefreshCw className={`w-4 h-4 ${analyticsLoading ? 'animate-spin' : ''}`} />
                        {analyticsLoading ? 'Loading...' : 'Load Analytics'}
                      </button>
                    </div>

                    {analyticsOverview ? (
                      <>
                        {/* Overview Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-gradient-to-br from-blue-500/20 to-blue-600/10 rounded-xl p-5 border border-blue-500/30">
                            <div className="flex items-center gap-3 mb-3">
                              <Users className="w-5 h-5 text-blue-400" />
                              <span className="text-xs text-gray-400">Total Users</span>
                            </div>
                            <p className="text-3xl font-bold text-white">{analyticsOverview.users?.total || 0}</p>
                            <p className="text-xs text-green-400 mt-1">+{analyticsOverview.users?.new_this_month || 0} this month</p>
                          </div>
                          <div className="bg-gradient-to-br from-green-500/20 to-green-600/10 rounded-xl p-5 border border-green-500/30">
                            <div className="flex items-center gap-3 mb-3">
                              <BarChart3 className="w-5 h-5 text-green-400" />
                              <span className="text-xs text-gray-400">Total Trades</span>
                            </div>
                            <p className="text-3xl font-bold text-white">{analyticsOverview.trades?.total || 0}</p>
                            <p className="text-xs text-green-400 mt-1">+{analyticsOverview.trades?.this_month || 0} this month</p>
                          </div>
                          <div className="bg-gradient-to-br from-purple-500/20 to-purple-600/10 rounded-xl p-5 border border-purple-500/30">
                            <div className="flex items-center gap-3 mb-3">
                              <Target className="w-5 h-5 text-purple-400" />
                              <span className="text-xs text-gray-400">Win Rate</span>
                            </div>
                            <p className="text-3xl font-bold text-white">{analyticsOverview.trades?.win_rate || 0}%</p>
                            <p className="text-xs text-gray-400 mt-1">{analyticsOverview.trades?.winning || 0}W / {analyticsOverview.trades?.losing || 0}L</p>
                          </div>
                          <div className={`bg-gradient-to-br rounded-xl p-5 border ${(analyticsOverview.trades?.total_pnl || 0) >= 0 ? 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30' : 'from-red-500/20 to-red-600/10 border-red-500/30'}`}>
                            <div className="flex items-center gap-3 mb-3">
                              <TrendingUp className={`w-5 h-5 ${(analyticsOverview.trades?.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`} />
                              <span className="text-xs text-gray-400">Total PnL</span>
                            </div>
                            <p className={`text-3xl font-bold ${(analyticsOverview.trades?.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                              ${(analyticsOverview.trades?.total_pnl || 0).toLocaleString()}
                            </p>
                          </div>
                        </div>

                        {/* Secondary Stats */}
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                            <span className="text-xs text-gray-400">Active Users</span>
                            <p className="text-xl font-bold text-white mt-1">{analyticsOverview.users?.active || 0}</p>
                          </div>
                          <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                            <span className="text-xs text-gray-400">Journal Access</span>
                            <p className="text-xl font-bold text-white mt-1">{analyticsOverview.users?.with_journal_access || 0}</p>
                          </div>
                          <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                            <span className="text-xs text-gray-400">Active Profiles</span>
                            <p className="text-xl font-bold text-white mt-1">{analyticsOverview.profiles?.active || 0}</p>
                          </div>
                          <div className="bg-[#0a1628] rounded-lg p-4 border border-[#2d4a6f]">
                            <span className="text-xs text-gray-400">Active Groups</span>
                            <p className="text-xl font-bold text-white mt-1">{analyticsOverview.groups?.active || 0}</p>
                          </div>
                        </div>

                        {/* Top Symbols & Users */}
                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          <div className="bg-[#0a1628] rounded-xl p-5 border border-[#2d4a6f]">
                            <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                              <Star className="w-4 h-4 text-yellow-400" />
                              Top Traded Symbols
                            </h4>
                            <div className="space-y-2 max-h-64 overflow-y-auto">
                              {topSymbols.length > 0 ? topSymbols.map((symbol, idx) => (
                                <div key={idx} className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg">
                                  <div className="flex items-center gap-3">
                                    <span className="w-6 h-6 flex items-center justify-center bg-blue-500/20 text-blue-400 rounded text-xs font-bold">{idx + 1}</span>
                                    <span className="font-medium text-white">{symbol.symbol}</span>
                                  </div>
                                  <div className="flex items-center gap-4 text-sm">
                                    <span className="text-gray-400">{symbol.trades} trades</span>
                                    <span className="text-blue-400">{symbol.total_pnl}</span>
                                  </div>
                                </div>
                              )) : <p className="text-gray-500 text-center py-4">No trade data</p>}
                            </div>
                          </div>
                          <div className="bg-[#0a1628] rounded-xl p-5 border border-[#2d4a6f]">
                            <h4 className="text-sm font-medium text-white mb-4 flex items-center gap-2">
                              <Award className="w-4 h-4 text-orange-400" />
                              Most Active Traders
                            </h4>
                            <div className="space-y-2 max-h-64 overflow-y-auto">
                              {topUsers.length > 0 ? topUsers.map((user, idx) => (
                                <div key={idx} className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg">
                                  <div className="flex items-center gap-3">
                                    <span className={`w-6 h-6 flex items-center justify-center rounded text-xs font-bold ${idx === 0 ? 'bg-yellow-500/20 text-yellow-400' : 'bg-blue-500/20 text-blue-400'}`}>{idx + 1}</span>
                                    <div>
                                      <p className="font-medium text-white text-sm">{user.name}</p>
                                      <p className="text-xs text-gray-500">{user.email}</p>
                                    </div>
                                  </div>
                                  <div className="text-right">
                                    <p className="text-sm text-white">{user.trades} trades</p>
                                    <p className="text-xs text-blue-400">{user.total_pnl}</p>
                                  </div>
                                </div>
                              )) : <p className="text-gray-500 text-center py-4">No user activity</p>}
                            </div>
                          </div>
                        </div>

                        {/* Groups */}
                        {groupAnalytics.length > 0 && (
                          <div className="bg-[#0a1628] rounded-xl p-5 border border-[#2d4a6f]">
                            <h4 className="text-sm font-medium text-white mb-4">Group Performance</h4>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                              {groupAnalytics.map((group, idx) => (
                                <div key={idx} className="p-4 bg-[#1e3a5f] rounded-lg border border-[#2d4a6f]">
                                  <div className="flex items-center justify-between mb-2">
                                    <h5 className="font-medium text-white">{group.name}</h5>
                                    <span className={`text-xs px-2 py-0.5 rounded ${group.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}`}>
                                      {group.is_active ? 'Active' : 'Inactive'}
                                    </span>
                                  </div>
                                  <div className="flex justify-between text-sm">
                                    <span className="text-gray-400">{group.user_count} users</span>
                                    <span className="text-blue-400">{group.trade_count} trades</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="text-center py-16 bg-[#0a1628] rounded-xl border border-[#2d4a6f]">
                        <TrendingUp className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-500 mb-4">Click "Load Analytics" to view data</p>
                        <button onClick={fetchAnalytics} disabled={analyticsLoading} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50">
                          {analyticsLoading ? 'Loading...' : 'Load Analytics'}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {/* Email Count Tab */}
                {activeAdminTab === 'email-count' && (
                  <div className="space-y-8">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-2">Email Prefix Counter</h3>
                        <p className="text-gray-600">Count users whose email addresses start with specific prefixes</p>
                      </div>
                    </div>

                    {/* Email Count Form */}
                    <div className="bg-gradient-to-br from-red-50 to-pink-50 rounded-2xl p-8 border border-red-200">
                      <div className="flex items-center gap-4 mb-8">
                        <div className="p-4 bg-red-100 rounded-2xl">
                          <Mail className="w-8 h-8 text-red-600" />
                        </div>
                        <div>
                          <h3 className="text-2xl font-bold text-gray-900">Count Users by Email Prefix</h3>
                          <p className="text-gray-600 text-lg">Enter an email prefix to count matching users</p>
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="md:col-span-2">
                          <label className="block text-sm font-semibold text-gray-700 mb-3">
                            <Mail className="w-4 h-4 inline mr-2" />
                            Email Prefix
                          </label>
                          <input
                            type="text"
                            value={emailPrefix}
                            onChange={(e) => setEmailPrefix(e.target.value)}
                            className="w-full px-5 py-4 border-2 border-gray-200 rounded-xl focus:ring-4 focus:ring-red-500/20 focus:border-red-500 transition-all duration-300 text-lg bg-white"
                            placeholder="Enter prefix (e.g., 'w', 'test', 'admin')"
                          />
                        </div>
                        <div className="flex items-end">
                          <button
                            onClick={handleEmailCount}
                            disabled={!emailPrefix.trim()}
                            className="w-full px-6 py-4 bg-red-600 text-white rounded-xl hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 font-semibold text-lg"
                          >
                            Count Users
                          </button>
                        </div>
                      </div>

                      {/* Results */}
                      {emailCountResult && (
                        <div className="mt-8 bg-white rounded-xl p-6 border border-gray-200">
                          <div className="flex items-center gap-4 mb-4">
                            <div className="p-3 bg-green-100 rounded-xl">
                              <CheckCircle className="w-6 h-6 text-green-600" />
                            </div>
                            <div>
                              <h4 className="text-lg font-bold text-gray-900">Count Results</h4>
                              <p className="text-gray-600">Results for prefix: <span className="font-semibold">"{emailCountResult.prefix}"</span></p>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white">
                              <div className="text-center">
                                <p className="text-green-100 text-sm font-semibold">Total Count</p>
                                <p className="text-5xl font-bold mt-2">{emailCountResult.count}</p>
                                <p className="text-green-200 text-sm mt-2">users found</p>
                              </div>
                            </div>
                            
                            <div className="bg-gray-50 rounded-xl p-6">
                              <h5 className="font-semibold text-gray-900 mb-3">Sample Emails</h5>
                              <div className="space-y-2">
                                {emailCountResult.sample_emails && emailCountResult.sample_emails.length > 0 ? (
                                  emailCountResult.sample_emails.map((email, index) => (
                                    <div key={index} className="text-sm text-gray-600 bg-white px-3 py-2 rounded-lg border">
                                      {email}
                                    </div>
                                  ))
                                ) : (
                                  <p className="text-sm text-gray-500">No sample emails available</p>
                                )}
                              </div>
                            </div>
                          </div>
                          
                          <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-200">
                            <p className="text-blue-800 font-medium">{emailCountResult.message}</p>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Quick Count Examples */}
                    <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl p-8 border border-gray-200">
                      <h4 className="text-lg font-bold text-gray-900 mb-6">Quick Count Examples</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {['w', 'test', 'admin', 'user'].map((prefix) => (
                          <button
                            key={prefix}
                            onClick={() => {
                              setEmailPrefix(prefix);
                              handleEmailCount(prefix);
                            }}
                            className="p-4 bg-white rounded-xl border border-gray-200 hover:border-red-300 hover:bg-red-50 transition-all duration-300 text-center"
                          >
                            <Mail className="w-6 h-6 text-red-600 mx-auto mb-2" />
                            <p className="font-semibold text-gray-900">"{prefix}"</p>
                            <p className="text-sm text-gray-600">prefix</p>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Geography Tab */}
                {activeAdminTab === 'geography' && (
                  <div className="space-y-6">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-gradient-to-br from-[#1e3a5f] to-[#2d4a6f] rounded-xl">
                          <Globe className="w-6 h-6 text-blue-400" />
                        </div>
                        <div>
                          <h3 className="text-xl font-bold text-white">User Geography & Demographics</h3>
                          <p className="text-gray-400 text-sm">Analyze user distribution by location</p>
                        </div>
                      </div>
                      <button onClick={() => fetchGeographyData(geographyFilter)} disabled={geographyLoading} className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm flex items-center gap-2 disabled:opacity-50">
                        {geographyLoading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                        Refresh
                      </button>
                    </div>

                    {/* Filter Buttons */}
                    <div className="flex flex-wrap gap-2">
                      {[{ id: 'all', label: 'All Users' }, { id: 'journal', label: 'Journal Users' }, { id: 'no-journal', label: 'No Journal' }, { id: 'mentorship', label: 'Mentorship' }].map(filter => (
                        <button key={filter.id} onClick={() => { setGeographyFilter(filter.id); fetchGeographyData(filter.id); }} className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${geographyFilter === filter.id ? 'bg-blue-600 text-white' : 'bg-[#1e3a5f] text-gray-400 hover:bg-[#2d4a6f] border border-[#2d4a6f]'}`}>
                          {filter.label}
                        </button>
                      ))}
                    </div>

                    {!geographyData && !geographyLoading && (
                      <div className="text-center py-12">
                        <Globe className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-400 mb-4">Click refresh to load geography data</p>
                        <button onClick={() => fetchGeographyData(geographyFilter)} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700">Load Data</button>
                      </div>
                    )}

                    {geographyLoading && (
                      <div className="text-center py-12">
                        <RefreshCw className="w-10 h-10 text-blue-400 animate-spin mx-auto" />
                        <p className="text-gray-400 mt-4">Loading...</p>
                      </div>
                    )}

                    {geographyData && !geographyLoading && (
                      <>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                          <div className="bg-[#0d1f35] rounded-xl p-5 border border-[#2d4a6f]">
                            <p className="text-gray-500 text-xs uppercase">Total Users</p>
                            <p className="text-3xl font-bold text-white mt-2">{geographyData.total_users}</p>
                          </div>
                          <div className="bg-[#0d1f35] rounded-xl p-5 border border-[#2d4a6f]">
                            <p className="text-gray-500 text-xs uppercase">Countries</p>
                            <p className="text-3xl font-bold text-blue-400 mt-2">{geographyData.all_countries?.length || 0}</p>
                          </div>
                          <div className="bg-[#0d1f35] rounded-xl p-5 border border-[#2d4a6f]">
                            <p className="text-gray-500 text-xs uppercase">Active (30d)</p>
                            <p className="text-3xl font-bold text-green-400 mt-2">{geographyData.user_breakdown?.active_users || 0}</p>
                          </div>
                          <div className="bg-[#0d1f35] rounded-xl p-5 border border-[#2d4a6f]">
                            <p className="text-gray-500 text-xs uppercase">Journal Users</p>
                            <p className="text-3xl font-bold text-purple-400 mt-2">{geographyData.user_breakdown?.journal_users || 0}</p>
                          </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                          <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><MapPin className="w-5 h-5 text-blue-400" />Top Countries</h4>
                            <div className="space-y-3 max-h-80 overflow-y-auto">
                              {geographyData.countries?.map((country, idx) => (
                                <div key={idx} className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg">
                                  <div className="flex items-center gap-3">
                                    <span className="text-gray-500 text-sm w-6">{idx + 1}.</span>
                                    <span className="text-white font-medium">{country.country}</span>
                                  </div>
                                  <div className="flex items-center gap-3">
                                    <div className="w-24 bg-[#0a1628] rounded-full h-2"><div className="bg-blue-500 h-2 rounded-full" style={{ width: `${country.percentage}%` }}></div></div>
                                    <span className="text-gray-400 text-sm w-20 text-right">{country.count} ({country.percentage}%)</span>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><Users className="w-5 h-5 text-green-400" />User Breakdown</h4>
                            <div className="space-y-4">
                              <div className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg"><span className="text-gray-300">Journal Users</span><span className="text-green-400 font-bold">{geographyData.user_breakdown?.journal_users || 0}</span></div>
                              <div className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg"><span className="text-gray-300">No Journal</span><span className="text-purple-400 font-bold">{geographyData.user_breakdown?.no_journal_users || 0}</span></div>
                              <div className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg"><span className="text-gray-300">Admins</span><span className="text-red-400 font-bold">{geographyData.user_breakdown?.admin_users || 0}</span></div>
                              <div className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg"><span className="text-gray-300">Active (30d)</span><span className="text-blue-400 font-bold">{geographyData.user_breakdown?.active_users || 0}</span></div>
                            </div>
                          </div>

                          <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><Mail className="w-5 h-5 text-purple-400" />Top Email Domains</h4>
                            <div className="space-y-2 max-h-60 overflow-y-auto">
                              {geographyData.email_domains?.map((domain, idx) => (
                                <div key={idx} className="flex items-center justify-between p-2 bg-[#1e3a5f] rounded-lg">
                                  <span className="text-gray-300 text-sm">@{domain.domain}</span>
                                  <span className="text-white font-medium">{domain.count}</span>
                                </div>
                              ))}
                            </div>
                          </div>

                          <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                            <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2"><BarChart3 className="w-5 h-5 text-yellow-400" />Age Distribution</h4>
                            <div className="space-y-3">
                              {geographyData.age_distribution?.map((age, idx) => {
                                const total = geographyData.age_distribution.reduce((sum, a) => sum + a.count, 0);
                                const pct = total > 0 ? Math.round((age.count / total) * 100) : 0;
                                return (
                                  <div key={idx} className="flex items-center justify-between p-3 bg-[#1e3a5f] rounded-lg">
                                    <span className="text-white font-medium">{age.range}</span>
                                    <div className="flex items-center gap-3">
                                      <div className="w-20 bg-[#0a1628] rounded-full h-2"><div className="bg-yellow-500 h-2 rounded-full" style={{ width: `${pct}%` }}></div></div>
                                      <span className="text-gray-400 text-sm w-16 text-right">{age.count} ({pct}%)</span>
                                    </div>
                                  </div>
                                );
                              })}
                            </div>
                          </div>
                        </div>
                      </>
                    )}
                  </div>
                )}

                {/* Feature Flags Tab */}
                {activeAdminTab === 'feature-flags' && (
                  <div className="space-y-8">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-2xl font-bold text-gray-900 mb-2">Feature Flags Management</h3>
                        <p className="text-gray-600">Control which features are visible to users</p>
                      </div>
                      <div className="flex items-center gap-3">
                        <button
                          onClick={handleResetFeatureFlags}
                          className="flex items-center px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors"
                        >
                          <RefreshCw className="w-4 h-4 mr-2" />
                          Reset
                        </button>
                        <button
                          onClick={handleSaveFeatureFlags}
                          disabled={isSavingFlags}
                          className="flex items-center px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                        >
                          <Save className="w-4 h-4 mr-2" />
                          {isSavingFlags ? 'Saving...' : 'Save Changes'}
                        </button>
                      </div>
                    </div>

                    {/* Status Message */}
                    {flagsMessage && (
                      <div className={`p-4 rounded-lg ${
                        flagsMessage.includes('Error') 
                          ? 'bg-red-50 text-red-700 border border-red-200' 
                          : 'bg-green-50 text-green-700 border border-green-200'
                      }`}>
                        {flagsMessage}
                      </div>
                    )}

                    {/* Feature Flags Summary */}
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                      <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
                        <div className="text-center">
                          <p className="text-blue-100 text-sm font-semibold">Total Flags</p>
                          <p className="text-3xl font-bold mt-2">{Object.keys(localFeatureFlags).length}</p>
                        </div>
                      </div>
                      
                      <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white">
                        <div className="text-center">
                          <p className="text-green-100 text-sm font-semibold">Enabled</p>
                          <p className="text-3xl font-bold mt-2">{Object.values(localFeatureFlags).filter(Boolean).length}</p>
                        </div>
                      </div>
                      
                      <div className="bg-gradient-to-br from-red-500 to-red-600 rounded-xl p-6 text-white">
                        <div className="text-center">
                          <p className="text-red-100 text-sm font-semibold">Disabled</p>
                          <p className="text-3xl font-bold mt-2">{Object.values(localFeatureFlags).filter(f => !f).length}</p>
                        </div>
                      </div>
                      
                      <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white">
                        <div className="text-center">
                          <p className="text-purple-100 text-sm font-semibold">Groups</p>
                          <p className="text-3xl font-bold mt-2">{Object.keys(FEATURE_GROUPS).length}</p>
                        </div>
                      </div>
                    </div>

                    {/* Feature Groups */}
                    <div className="space-y-6">
                      {Object.entries(FEATURE_GROUPS).map(([groupName, features]) => (
                        <div key={groupName} className="border border-gray-200 rounded-xl p-6 bg-white/50">
                          <div className="flex items-center justify-between mb-4">
                            <h4 className="text-lg font-semibold text-gray-900 capitalize">
                              {groupName.replace('_', ' ')} Features
                            </h4>
                            <div className="flex items-center space-x-2">
                              <button
                                onClick={() => handleToggleFeatureGroup(groupName, true)}
                                className="px-3 py-1 text-xs font-medium text-green-700 bg-green-100 rounded hover:bg-green-200"
                              >
                                Enable All
                              </button>
                              <button
                                onClick={() => handleToggleFeatureGroup(groupName, false)}
                                className="px-3 py-1 text-xs font-medium text-red-700 bg-red-100 rounded hover:bg-red-200"
                              >
                                Disable All
                              </button>
                            </div>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {features.map(feature => (
                              <div key={feature} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                                <div>
                                  <p className="font-medium text-gray-900">
                                    {feature.replace(/_/g, ' ')}
                                  </p>
                                  <p className="text-sm text-gray-500">
                                    {localFeatureFlags[feature] ? 'Enabled' : 'Disabled'}
                                  </p>
                                </div>
                                <button
                                  onClick={() => handleToggleFeature(feature)}
                                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                                    localFeatureFlags[feature] ? 'bg-blue-600' : 'bg-gray-200'
                                  }`}
                                >
                                  <span
                                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                      localFeatureFlags[feature] ? 'translate-x-6' : 'translate-x-1'
                                    }`}
                                  />
                                </button>
                              </div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Individual Features (not in groups) */}
                    <div className="border border-gray-200 rounded-xl p-6 bg-white/50">
                      <h4 className="text-lg font-semibold text-gray-900 mb-4">Other Features</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {Object.entries(localFeatureFlags)
                          .filter(([feature]) => !Object.values(FEATURE_GROUPS).flat().includes(feature))
                          .map(([feature, enabled]) => (
                            <div key={feature} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                              <div>
                                <p className="font-medium text-gray-900">
                                  {feature.replace(/_/g, ' ')}
                                </p>
                                <p className="text-sm text-gray-500">
                                  {enabled ? 'Enabled' : 'Disabled'}
                                </p>
                              </div>
                              <button
                                onClick={() => handleToggleFeature(feature)}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                                  enabled ? 'bg-blue-600' : 'bg-gray-200'
                                }`}
                              >
                                <span
                                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                    enabled ? 'translate-x-6' : 'translate-x-1'
                                  }`}
                                />
                              </button>
                            </div>
                          ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Bulk Email Tab */}
                {activeAdminTab === 'bulk-email' && (
                  <BulkEmailManager users={users} />
                )}

                {/* Newsletter Tab */}
                {activeAdminTab === 'newsletter' && (
                  <NewsletterManager />
                )}

                {/* Settings Tab */}
                {activeAdminTab === 'settings' && (
                  <div className="space-y-6">
                    {/* Header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-3 bg-gradient-to-br from-[#1e3a5f] to-[#2d4a6f] rounded-xl">
                          <Shield className="w-6 h-6 text-blue-400" />
                        </div>
                        <div>
                          <h3 className="text-xl font-bold text-white">Security Settings</h3>
                          <p className="text-gray-400 text-sm">Configure security policies and thresholds</p>
                        </div>
                      </div>
                      <div className="flex gap-3">
                        <button
                          onClick={resetSecuritySettings}
                          className="px-4 py-2 bg-[#1e3a5f] text-gray-300 rounded-lg hover:bg-[#2d4a6f] border border-[#2d4a6f] transition-all text-sm"
                        >
                          Reset to Defaults
                        </button>
                        <button
                          onClick={saveSecuritySettings}
                          disabled={savingSettings}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all text-sm flex items-center gap-2 disabled:opacity-50"
                        >
                          {savingSettings ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                          Save Changes
                        </button>
                      </div>
                    </div>

                    {Object.keys(securitySettings).length === 0 && !securitySettingsLoading && (
                      <div className="text-center py-8">
                        <button onClick={fetchSecuritySettings} className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all">
                          Load Security Settings
                        </button>
                      </div>
                    )}

                    {securitySettingsLoading && (
                      <div className="text-center py-8">
                        <RefreshCw className="w-8 h-8 text-blue-400 animate-spin mx-auto" />
                        <p className="text-gray-400 mt-2">Loading settings...</p>
                      </div>
                    )}

                    {Object.keys(securitySettings).length > 0 && (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* IP Blocking Settings */}
                        <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                          <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Ban className="w-5 h-5 text-red-400" />
                            IP Blocking
                          </h4>
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm text-gray-400 mb-1">Max Failed Attempts Before Block</label>
                              <input type="number" value={securitySettings.max_failed_attempts?.value || '10'} onChange={(e) => updateSecuritySetting('max_failed_attempts', e.target.value)} className="w-full px-4 py-2.5 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white focus:border-blue-500" />
                            </div>
                            <div>
                              <label className="block text-sm text-gray-400 mb-1">Block Duration (hours)</label>
                              <input type="number" value={securitySettings.block_duration_hours?.value || '24'} onChange={(e) => updateSecuritySetting('block_duration_hours', e.target.value)} className="w-full px-4 py-2.5 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white focus:border-blue-500" />
                            </div>
                            <div className="flex items-center justify-between pt-2">
                              <span className="text-gray-300">Auto-Block Enabled</span>
                              <button onClick={() => updateSecuritySetting('auto_block_enabled', securitySettings.auto_block_enabled?.value === 'true' ? 'false' : 'true')} className={`relative w-12 h-6 rounded-full transition-colors ${securitySettings.auto_block_enabled?.value === 'true' ? 'bg-blue-600' : 'bg-gray-600'}`}>
                                <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${securitySettings.auto_block_enabled?.value === 'true' ? 'left-7' : 'left-1'}`} />
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Alert Settings */}
                        <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                          <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Bell className="w-5 h-5 text-yellow-400" />
                            Alerts
                          </h4>
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm text-gray-400 mb-1">Alert Threshold (attempts before alert)</label>
                              <input type="number" value={securitySettings.alert_threshold?.value || '5'} onChange={(e) => updateSecuritySetting('alert_threshold', e.target.value)} className="w-full px-4 py-2.5 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white focus:border-blue-500" />
                            </div>
                            <div className="flex items-center justify-between pt-2">
                              <span className="text-gray-300">Email Alerts Enabled</span>
                              <button onClick={() => updateSecuritySetting('alert_email_enabled', securitySettings.alert_email_enabled?.value === 'true' ? 'false' : 'true')} className={`relative w-12 h-6 rounded-full transition-colors ${securitySettings.alert_email_enabled?.value === 'true' ? 'bg-blue-600' : 'bg-gray-600'}`}>
                                <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${securitySettings.alert_email_enabled?.value === 'true' ? 'left-7' : 'left-1'}`} />
                              </button>
                            </div>
                          </div>
                        </div>

                        {/* Session Settings */}
                        <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                          <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Clock className="w-5 h-5 text-green-400" />
                            Session
                          </h4>
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm text-gray-400 mb-1">Session Timeout (minutes)</label>
                              <input type="number" value={securitySettings.session_timeout_minutes?.value || '60'} onChange={(e) => updateSecuritySetting('session_timeout_minutes', e.target.value)} className="w-full px-4 py-2.5 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white focus:border-blue-500" />
                            </div>
                          </div>
                        </div>

                        {/* Password Policy */}
                        <div className="bg-[#0d1f35] rounded-xl p-6 border border-[#2d4a6f]">
                          <h4 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Lock className="w-5 h-5 text-purple-400" />
                            Password Policy
                          </h4>
                          <div className="space-y-4">
                            <div>
                              <label className="block text-sm text-gray-400 mb-1">Minimum Password Length</label>
                              <input type="number" value={securitySettings.min_password_length?.value || '8'} onChange={(e) => updateSecuritySetting('min_password_length', e.target.value)} className="w-full px-4 py-2.5 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white focus:border-blue-500" />
                            </div>
                            <div className="flex items-center justify-between pt-2">
                              <span className="text-gray-300">Require Strong Password</span>
                              <button onClick={() => updateSecuritySetting('require_strong_password', securitySettings.require_strong_password?.value === 'true' ? 'false' : 'true')} className={`relative w-12 h-6 rounded-full transition-colors ${securitySettings.require_strong_password?.value === 'true' ? 'bg-blue-600' : 'bg-gray-600'}`}>
                                <span className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${securitySettings.require_strong_password?.value === 'true' ? 'left-7' : 'left-1'}`} />
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Profile Information Section - Hidden for admin users */}
        {!isAdmin && (
        <div className="max-w-4xl mx-auto mb-12">
            <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-2xl border border-white/50 overflow-hidden">
              {/* Card Header */}
              <div className="bg-gradient-to-r from-gray-50 to-gray-100 px-8 py-6 border-b border-gray-200/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-100 rounded-xl">
                      <User className="w-6 h-6 text-blue-600" />
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-gray-900">Profile Information</h2>
                      <p className="text-gray-600">Update your personal details and preferences</p>
                    </div>
                  </div>
                  {hasChanges && (
                    <div className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold bg-amber-100 text-amber-800 border border-amber-200 animate-pulse">
                      <AlertCircle className="w-4 h-4" />
                      Unsaved Changes
                    </div>
                  )}
                </div>
              </div>

              <div className="p-8 space-y-8">
                {/* Profile Image Section */}
                <div className="text-center pb-8 border-b border-gray-100">
                  <div className="relative inline-block group">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-indigo-500 rounded-full blur-md opacity-50 group-hover:opacity-75 transition-opacity"></div>
                    <div className="relative w-40 h-40 rounded-full bg-gradient-to-r from-blue-400 to-indigo-500 flex items-center justify-center overflow-hidden shadow-2xl group-hover:scale-105 transition-transform duration-300">
                      {previewImage ? (
                        <img
                          src={previewImage}
                          alt="Profile"
                          className="w-full h-full object-cover"
                          onError={() => setPreviewImage('')}
                        />
                      ) : (
                        <User className="w-20 h-20 text-white" />
                      )}
                    </div>
                    <div className="absolute -bottom-3 -right-3 w-12 h-12 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform">
                      <Camera className="w-6 h-6 text-white" />
                    </div>
                  </div>
                  <p className="text-gray-500 mt-4 text-lg">Upload a photo to personalize your account</p>
                </div>

                {/* Form Fields */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Left Column */}
                  <div className="space-y-6">
                    {/* Profile Image URL */}
                    <div className="space-y-3">
                      <label className="flex items-center gap-3 text-sm font-semibold text-gray-700">
                        <div className="p-2 bg-purple-100 rounded-lg">
                          <Image className="w-4 h-4 text-purple-600" />
                        </div>
                        Profile Image URL
                      </label>
                      <input
                        type="url"
                        value={profileImage}
                        onChange={handleImageChange}
                        className="w-full px-5 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-300 text-lg bg-gray-50/50"
                        placeholder="https://example.com/your-photo.jpg"
                      />
                      <p className="text-sm text-gray-500 ml-1">Paste a URL to your profile image</p>
                    </div>

                    {/* Email */}
                    <div className="space-y-3">
                      <label className="flex items-center gap-3 text-sm font-semibold text-gray-700">
                        <div className="p-2 bg-green-100 rounded-lg">
                          <Mail className="w-4 h-4 text-green-600" />
                        </div>
                        Email Address
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full px-5 py-4 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-300 text-lg bg-gray-50/50"
                        required
                        placeholder="your@email.com"
                      />
                    </div>
                  </div>

                  {/* Right Column */}
                  <div className="space-y-6">
                    {/* Password */}
                    <div className="space-y-3">
                      <label className="flex items-center gap-3 text-sm font-semibold text-gray-700">
                        <div className="p-2 bg-red-100 rounded-lg">
                          <Lock className="w-4 h-4 text-red-600" />
                        </div>
                        New Password
                        <span className="text-xs text-gray-500 font-normal ml-2">(leave blank to keep current)</span>
                      </label>
                      <div className="relative">
                        <input
                          type={showPassword ? 'text' : 'password'}
                          value={password}
                          onChange={(e) => setPassword(e.target.value)}
                          className="w-full px-5 py-4 pr-14 border-2 border-gray-200 rounded-2xl focus:ring-4 focus:ring-blue-500/20 focus:border-blue-500 transition-all duration-300 text-lg bg-gray-50/50"
                          placeholder="Enter new password"
                        />
                        <button
                          type="button"
                          onClick={() => setShowPassword(!showPassword)}
                          className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors p-2 rounded-lg hover:bg-gray-100"
                        >
                          {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                        </button>
                      </div>
                      <p className="text-sm text-gray-500 ml-1">Must be at least 8 characters long</p>
                    </div>

                    {/* Logout Section */}
                    <div className="bg-gradient-to-r from-red-50 to-red-100 rounded-2xl p-6 border border-red-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="p-2 bg-red-100 rounded-lg">
                            <LogOut className="w-5 h-5 text-red-600" />
                          </div>
                          <div>
                            <h3 className="text-lg font-bold text-gray-900">Sign Out</h3>
                            <p className="text-sm text-gray-600">Sign out of your account</p>
                          </div>
                        </div>
                        <button
                          onClick={handleLogout}
                          className="flex items-center gap-2 px-4 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 rounded-xl transition-all duration-300 font-semibold border border-red-200 hover:border-red-300"
                        >
                          <LogOut className="w-4 h-4" />
                          Sign Out
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Save Button */}
                <div className="pt-6">
                  <button
                    type="button"
                    onClick={handleSave}
                    disabled={loading || !hasChanges}
                    className={`w-full flex items-center justify-center gap-3 py-5 px-8 rounded-2xl font-bold text-lg transition-all duration-300 transform ${
                      loading || !hasChanges
                        ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                        : 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white hover:from-blue-700 hover:to-indigo-700 shadow-2xl hover:shadow-3xl hover:scale-105 active:scale-95'
                    }`}
                  >
                    {loading ? (
                      <>
                        <div className="w-6 h-6 border-3 border-gray-400 border-t-transparent rounded-full animate-spin" />
                        Saving Changes...
                      </>
                    ) : (
                      <>
                        <Save className="w-6 h-6" />
                        Save Changes
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
        {/* Footer */}
        <div className="text-center mt-12 p-6 bg-white/50 backdrop-blur-sm rounded-2xl border border-white/50">
          <p className="text-gray-600 text-lg">Your data is encrypted and secure. We never share your information.</p>
          <div className="flex items-center justify-center gap-2 mt-2 text-sm text-gray-500">
            <Shield className="w-4 h-4" />
            <span>Protected by enterprise-grade security</span>
          </div>
        </div>
      </div>
      {showEditModal && (
  <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
    <div className="bg-white rounded-2xl shadow-2xl p-8 w-full max-w-md relative">
      <button onClick={() => setShowEditModal(false)} className="absolute top-4 right-4 text-gray-400 hover:text-gray-700"><X className="w-6 h-6" /></button>
      <h3 className="text-2xl font-bold mb-6 flex items-center gap-2"><Edit className="w-6 h-6 text-blue-600" /> Edit User</h3>
      {editError && <div className="mb-4 text-red-600 text-sm">{editError}</div>}
      {editUser ? (
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-semibold mb-1">Email</label>
            <input type="email" value={editUser.email} onChange={e => setEditUser({ ...editUser, email: e.target.value })} className="w-full border rounded-lg px-4 py-2" />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Full Name</label>
            <input type="text" value={editUser.full_name || ''} onChange={e => setEditUser({ ...editUser, full_name: e.target.value })} className="w-full border rounded-lg px-4 py-2" />
          </div>
          <div>
            <label className="block text-sm font-semibold mb-1">Country</label>
            <input type="text" value={editUser.country || ''} onChange={e => setEditUser({ ...editUser, country: e.target.value })} className="w-full border rounded-lg px-4 py-2" />
          </div>
          <div className="flex items-center gap-2">
            <input type="checkbox" id="edit_is_admin" checked={!!editUser.is_admin} onChange={e => setEditUser({ ...editUser, is_admin: e.target.checked })} className="h-5 w-5" />
            <label htmlFor="edit_is_admin" className="text-sm font-semibold">Admin privileges</label>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <input type="checkbox" id="edit_email_verified" checked={!!editUser.email_verified} onChange={e => setEditUser({ ...editUser, email_verified: e.target.checked })} className="h-5 w-5" />
            <label htmlFor="edit_email_verified" className="text-sm font-semibold">Email Verified</label>
            {editUser.email_verified && <CheckCircle className="w-5 h-5 text-green-500 ml-1" />}
          </div>
        </div>
      ) : (
        <div className="text-gray-500">No user data loaded.</div>
      )}
      <button onClick={handleSaveEditUser} disabled={editLoading} className="mt-8 w-full bg-blue-600 text-white font-bold py-3 rounded-xl hover:bg-blue-700 transition-all duration-300 flex items-center justify-center gap-2 disabled:opacity-50">
        {editLoading ? <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent" /> : <Edit className="w-5 h-5" />} Save Changes
      </button>
    </div>
  </div>
)}
    </div>
    
  );
}