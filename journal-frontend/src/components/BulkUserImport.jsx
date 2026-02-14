import React, { useState } from 'react';

const BulkUserImport = () => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [results, setResults] = useState(null);
  const [userSource, setUserSource] = useState('talaria-prop');
  const [hasJournalAccess, setHasJournalAccess] = useState(false);

  const API_BASE_URL = '/api';

  const downloadTemplate = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`${API_BASE_URL}/admin/download-user-template`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'bulk_users_template.csv';
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (error) {
      alert('Error downloading template');
    }
  };

  const uploadFile = async () => {
    if (!file) return;
    setUploading(true);
    try {
      const token = localStorage.getItem('token');
      const formData = new FormData();
      formData.append('file', file);
      formData.append('user_source', userSource);
      formData.append('has_journal_access', hasJournalAccess);
      const response = await fetch(`${API_BASE_URL}/admin/import-users`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });
      setResults(await response.json());
      if (response.ok) setFile(null);
    } catch (error) {
      setResults({ success: false, error: 'Network error' });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="bg-[#0a1628] rounded-xl p-6 border border-[#2d4a6f]">
        <h4 className="text-lg font-semibold mb-4 text-white">📋 Required Columns</h4>
        <p className="text-gray-400 mb-4">Your CSV/XLSX file must have these columns:</p>
        <div className="bg-[#1e3a5f] rounded-lg p-4 mb-4">
          <code className="text-sm text-green-400">first_name, last_name, email</code>
          <p className="text-xs text-gray-500 mt-2">Optional: phone, country, password</p>
        </div>
        <p className="text-xs text-gray-500">If password is empty, a random one will be generated. If password looks hashed (starts with scrypt: or pbkdf2:), it will be used as-is.</p>
      </div>
      
      <div className="bg-[#0a1628] rounded-xl p-6 border border-[#2d4a6f]">
        <h4 className="text-lg font-semibold mb-4 text-white">📤 Upload Users</h4>
        
        {/* User Source Selection */}
        <div className="mb-4">
          <label className="block text-sm text-gray-400 mb-2">User Source / Category</label>
          <select 
            value={userSource} 
            onChange={(e) => setUserSource(e.target.value)}
            className="w-full px-3 py-2 bg-[#1e3a5f] border border-[#2d4a6f] rounded-lg text-white text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="talaria-prop">Talaria-prop</option>
            <option value="mentorship">Mentorship</option>
            <option value="organic">Organic</option>
            <option value="other">Other</option>
          </select>
        </div>

        {/* Journal Access Checkbox */}
        <div className="mb-4">
          <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
            <input
              type="checkbox"
              checked={hasJournalAccess}
              onChange={(e) => setHasJournalAccess(e.target.checked)}
              className="h-4 w-4 rounded border-[#2d4a6f] bg-[#1e3a5f] text-blue-500"
            />
            Grant Journal Access to imported users
          </label>
        </div>

        {/* File Input */}
        <input 
          type="file" 
          onChange={(e) => setFile(e.target.files[0])} 
          accept=".csv,.xlsx,.xls" 
          className="mb-4 block w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-600 file:text-white hover:file:bg-blue-700 cursor-pointer"
        />
        {file && (
          <div className="mt-4">
            <p className="text-sm text-gray-400 mb-2">Selected: <span className="text-white">{file.name}</span></p>
            <button 
              onClick={uploadFile} 
              disabled={uploading} 
              className="bg-green-600 hover:bg-green-700 disabled:bg-gray-600 text-white px-6 py-3 rounded-lg font-medium"
            >
              {uploading ? '⏳ Importing...' : '🚀 Import Users'}
            </button>
          </div>
        )}
      </div>
      
      {results && (
        <div className={`p-4 rounded-lg border ${results.created > 0 ? 'bg-green-900/30 border-green-600' : 'bg-red-900/30 border-red-600'}`}>
          <h5 className="font-medium mb-2 text-white">{results.created > 0 ? '✅ Import Completed!' : '❌ Import Failed'}</h5>
          <p className="text-sm text-gray-300">
            {results.message || (results.created > 0 
              ? `Created ${results.created} users${results.skipped > 0 ? `, ${results.skipped} skipped` : ''}` 
              : results.detail || 'Unknown error'
            )}
          </p>
          {results.errors && results.errors.length > 0 && (
            <div className="mt-3">
              <p className="text-sm font-medium text-gray-300">Details (first 20):</p>
              <ul className="text-xs list-disc list-inside text-gray-400 mt-1 max-h-32 overflow-y-auto">
                {results.errors.slice(0, 20).map((error, index) => (
                  <li key={index}>Row {error.row}: {error.error} {error.email && `(${error.email})`}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
      
      <div className="bg-[#0a1628] rounded-xl p-6 border border-[#2d4a6f]">
        <h4 className="text-lg font-semibold mb-4 text-white">🎯 User Sources</h4>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
          <div className="bg-[#1e3a5f] rounded-lg p-3 border border-[#2d4a6f]">
            <h5 className="font-medium text-orange-400">🏢 Talaria-prop</h5>
            <p className="text-gray-400">Prop firm users</p>
          </div>
          <div className="bg-[#1e3a5f] rounded-lg p-3 border border-[#2d4a6f]">
            <h5 className="font-medium text-purple-400">🎓 Mentorship</h5>
            <p className="text-gray-400">Mentorship students</p>
          </div>
          <div className="bg-[#1e3a5f] rounded-lg p-3 border border-[#2d4a6f]">
            <h5 className="font-medium text-green-400">🌱 Organic</h5>
            <p className="text-gray-400">Self-registered users</p>
          </div>
          <div className="bg-[#1e3a5f] rounded-lg p-3 border border-[#2d4a6f]">
            <h5 className="font-medium text-gray-400">� Other</h5>
            <p className="text-gray-400">Other sources</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BulkUserImport;
