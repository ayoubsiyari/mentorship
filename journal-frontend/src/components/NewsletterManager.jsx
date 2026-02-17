import React, { useState, useEffect, useCallback } from 'react';
import { Mail, Users, Send, CheckCircle, AlertCircle, Search, Trash2, RefreshCw, Eye, Bold, Italic, Underline as UnderlineIcon, Link2, Image, AlignLeft, AlignCenter, AlignRight, List, ListOrdered, Type, Maximize2, Minimize2 } from 'lucide-react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import UnderlineExtension from '@tiptap/extension-underline';
import LinkExtension from '@tiptap/extension-link';
import TextAlign from '@tiptap/extension-text-align';
import ImageExtension from '@tiptap/extension-image';
import { Color } from '@tiptap/extension-color';
import { TextStyle } from '@tiptap/extension-text-style';

const MenuBar = ({ editor }) => {
  const [showLinkInput, setShowLinkInput] = useState(false);
  const [linkUrl, setLinkUrl] = useState('');
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [uploading, setUploading] = useState(false);

  if (!editor) return null;

  const addLink = () => {
    if (linkUrl) {
      editor.chain().focus().extendMarkRange('link').setLink({ href: linkUrl }).run();
      setLinkUrl('');
      setShowLinkInput(false);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);

      const token = localStorage.getItem('token');
      const response = await fetch('/api/newsletter/admin/upload-image', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (response.ok) {
        const data = await response.json();
        editor.chain().focus().setImage({ src: data.url }).run();
      }
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const colors = ['#000000', '#ef4444', '#f97316', '#eab308', '#22c55e', '#3b82f6', '#8b5cf6', '#ec4899'];

  return (
    <div className="border-b border-[#2d4a6f] p-2 flex flex-wrap gap-1 items-center bg-[#0a1628]">
      {/* Text Style */}
      <button
        onClick={() => editor.chain().focus().toggleBold().run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive('bold') ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Bold"
      >
        <Bold className="w-4 h-4" />
      </button>
      <button
        onClick={() => editor.chain().focus().toggleItalic().run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive('italic') ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Italic"
      >
        <Italic className="w-4 h-4" />
      </button>
      <button
        onClick={() => editor.chain().focus().toggleUnderline().run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive('underline') ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Underline"
      >
        <UnderlineIcon className="w-4 h-4" />
      </button>

      <div className="w-px h-6 bg-[#2d4a6f] mx-1" />

      {/* Colors */}
      <div className="relative">
        <button 
          onClick={() => setShowColorPicker(!showColorPicker)}
          className="p-2 rounded hover:bg-white/10 transition-colors text-gray-400" 
          title="Text Color"
        >
          <Type className="w-4 h-4" />
        </button>
        {showColorPicker && (
          <div className="absolute top-full left-0 mt-1 p-2 bg-[#1e3a5f] rounded-lg shadow-xl flex gap-1 z-10">
            {colors.map((color) => (
              <button
                key={color}
                onClick={() => {
                  editor.chain().focus().setColor(color).run();
                  setShowColorPicker(false);
                }}
                className="w-6 h-6 rounded border border-gray-600 hover:scale-110 transition-transform"
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
        )}
      </div>

      <div className="w-px h-6 bg-[#2d4a6f] mx-1" />

      {/* Alignment */}
      <button
        onClick={() => editor.chain().focus().setTextAlign('left').run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive({ textAlign: 'left' }) ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Align Left"
      >
        <AlignLeft className="w-4 h-4" />
      </button>
      <button
        onClick={() => editor.chain().focus().setTextAlign('center').run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive({ textAlign: 'center' }) ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Align Center"
      >
        <AlignCenter className="w-4 h-4" />
      </button>
      <button
        onClick={() => editor.chain().focus().setTextAlign('right').run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive({ textAlign: 'right' }) ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Align Right"
      >
        <AlignRight className="w-4 h-4" />
      </button>

      <div className="w-px h-6 bg-[#2d4a6f] mx-1" />

      {/* Lists */}
      <button
        onClick={() => editor.chain().focus().toggleBulletList().run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive('bulletList') ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Bullet List"
      >
        <List className="w-4 h-4" />
      </button>
      <button
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
        className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive('orderedList') ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
        title="Numbered List"
      >
        <ListOrdered className="w-4 h-4" />
      </button>

      <div className="w-px h-6 bg-[#2d4a6f] mx-1" />

      {/* Link */}
      <div className="relative">
        <button
          onClick={() => setShowLinkInput(!showLinkInput)}
          className={`p-2 rounded hover:bg-white/10 transition-colors ${editor.isActive('link') ? 'bg-blue-500/30 text-blue-400' : 'text-gray-400'}`}
          title="Insert Link"
        >
          <Link2 className="w-4 h-4" />
        </button>
        {showLinkInput && (
          <div className="absolute top-full left-0 mt-1 p-2 bg-[#1e3a5f] rounded-lg shadow-xl z-10 flex gap-2">
            <input
              type="url"
              value={linkUrl}
              onChange={(e) => setLinkUrl(e.target.value)}
              placeholder="https://..."
              className="px-2 py-1 bg-[#0a1628] border border-[#2d4a6f] rounded text-white text-sm w-48"
              onKeyDown={(e) => e.key === 'Enter' && addLink()}
            />
            <button onClick={addLink} className="px-2 py-1 bg-blue-500 text-white rounded text-sm">Add</button>
          </div>
        )}
      </div>

      {/* Image Upload */}
      <label className="relative cursor-pointer">
        <input
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          className="hidden"
          disabled={uploading}
        />
        <div
          className={`p-2 rounded hover:bg-white/10 transition-colors text-gray-400 ${uploading ? 'opacity-50' : ''}`}
          title="Upload Image"
        >
          <Image className="w-4 h-4" />
        </div>
      </label>
    </div>
  );
};

const NewsletterManager = () => {
  const [subscribers, setSubscribers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({ total: 0, active: 0 });
  const [searchQuery, setSearchQuery] = useState('');
  const [activeOnly, setActiveOnly] = useState(false);
  
  // Send newsletter form
  const [subject, setSubject] = useState('');
  const [sending, setSending] = useState(false);
  const [result, setResult] = useState(null);
  const [showPreview, setShowPreview] = useState(false);
  const [editorExpanded, setEditorExpanded] = useState(false);

  // Rich text editor
  const editor = useEditor({
    extensions: [
      StarterKit,
      UnderlineExtension,
      LinkExtension.configure({ openOnClick: false }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      ImageExtension,
      TextStyle,
      Color,
    ],
    content: '<p>اكتب محتوى النشرة هنا...</p>',
    editorProps: {
      attributes: {
        class: 'prose prose-invert max-w-none min-h-[200px] p-4 focus:outline-none text-white',
      },
    },
  });

  const getContent = useCallback(() => {
    return editor ? editor.getHTML() : '';
  }, [editor]);

  // Fetch subscribers
  const fetchSubscribers = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/newsletter/admin/subscribers?active_only=${activeOnly}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        const data = await response.json();
        setSubscribers(data.subscribers || []);
        setStats({ total: data.total, active: data.active_count });
      }
    } catch (err) {
      console.error('Failed to fetch subscribers:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSubscribers();
  }, [activeOnly]);

  // Filter subscribers by search
  const filteredSubscribers = subscribers.filter(sub => 
    sub.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (sub.name && sub.name.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  // Delete subscriber
  const handleDelete = async (subscriberId) => {
    if (!window.confirm('Are you sure you want to delete this subscriber?')) return;
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/newsletter/admin/subscribers/${subscriberId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (response.ok) {
        fetchSubscribers();
      }
    } catch (err) {
      console.error('Failed to delete subscriber:', err);
    }
  };

  // Send newsletter
  const handleSendNewsletter = async () => {
    const content = getContent();
    if (!subject.trim() || !content || content === '<p></p>') {
      setResult({ success: false, message: 'Please enter subject and content' });
      return;
    }

    setSending(true);
    setResult(null);

    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/newsletter/admin/send', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          subject,
          content,
          send_to_all: true
        })
      });

      const data = await response.json();

      if (response.ok) {
        setResult({
          success: true,
          message: data.message || `Sent to ${data.sent_count} subscribers`
        });
        setSubject('');
        editor?.commands.setContent('<p>اكتب محتوى النشرة هنا...</p>');
      } else {
        setResult({
          success: false,
          message: data.detail || 'Failed to send newsletter'
        });
      }
    } catch (err) {
      setResult({
        success: false,
        message: 'Network error: ' + err.message
      });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="w-full bg-[#0a1628] rounded-2xl border border-[#1e3a5f] overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-[#1e3a5f] to-[#0a1628] p-6 border-b border-[#2d4a6f]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Mail className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-white">Newsletter Manager</h2>
              <p className="text-gray-400 text-sm">Manage subscribers and send newsletters</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center px-4 py-2 bg-[#0a1628] rounded-xl border border-[#2d4a6f]">
              <p className="text-2xl font-bold text-emerald-400">{stats.active}</p>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">Active</p>
            </div>
            <div className="text-center px-4 py-2 bg-[#0a1628] rounded-xl border border-[#2d4a6f]">
              <p className="text-2xl font-bold text-gray-400">{stats.total}</p>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">Total</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6">
        {/* Subscribers List */}
        <div className="bg-[#0d1f35] rounded-xl border border-[#2d4a6f] overflow-hidden">
          <div className="p-4 border-b border-[#2d4a6f]">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                <Users className="w-5 h-5 text-emerald-400" />
                Subscribers
              </h3>
              <button
                onClick={fetchSubscribers}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                title="Refresh"
              >
                <RefreshCw className={`w-4 h-4 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
            <div className="flex items-center gap-3">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                <input
                  type="text"
                  placeholder="Search subscribers..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-[#0a1628] border border-[#2d4a6f] rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500/50"
                />
              </div>
              <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={activeOnly}
                  onChange={(e) => setActiveOnly(e.target.checked)}
                  className="rounded border-gray-600 bg-[#0a1628] text-emerald-500 focus:ring-emerald-500/50"
                />
                Active only
              </label>
            </div>
          </div>
          
          <div className="max-h-[400px] overflow-y-auto">
            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading...</div>
            ) : filteredSubscribers.length === 0 ? (
              <div className="p-8 text-center text-gray-500">No subscribers found</div>
            ) : (
              <div className="divide-y divide-[#2d4a6f]">
                {filteredSubscribers.map((sub) => (
                  <div key={sub.id} className="p-4 hover:bg-white/5 transition-colors">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-white font-medium">{sub.email}</p>
                        <div className="flex items-center gap-3 mt-1">
                          {sub.name && <span className="text-gray-400 text-sm">{sub.name}</span>}
                          <span className={`text-xs px-2 py-0.5 rounded-full ${
                            sub.is_active 
                              ? 'bg-emerald-500/20 text-emerald-400' 
                              : 'bg-red-500/20 text-red-400'
                          }`}>
                            {sub.is_active ? 'Active' : 'Unsubscribed'}
                          </span>
                          {sub.source && (
                            <span className="text-xs text-gray-500">{sub.source}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => handleDelete(sub.id)}
                        className="p-2 hover:bg-red-500/20 rounded-lg transition-colors text-gray-400 hover:text-red-400"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Send Newsletter */}
        <div className="bg-[#0d1f35] rounded-xl border border-[#2d4a6f] overflow-hidden">
          <div className="p-4 border-b border-[#2d4a6f]">
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Send className="w-5 h-5 text-blue-400" />
              Send Newsletter
            </h3>
          </div>
          
          <div className="p-4 space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Subject</label>
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Newsletter subject..."
                className="w-full px-4 py-3 bg-[#0a1628] border border-[#2d4a6f] rounded-lg text-white focus:outline-none focus:border-blue-500/50"
              />
            </div>
            
            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="block text-sm text-gray-400">Content</label>
                <button
                  onClick={() => setEditorExpanded(!editorExpanded)}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-gray-400 hover:text-white bg-[#0a1628] border border-[#2d4a6f] rounded hover:border-blue-500/50 transition-colors"
                  title={editorExpanded ? 'Collapse' : 'Expand'}
                >
                  {editorExpanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
                  {editorExpanded ? 'Collapse' : 'Expand'}
                </button>
              </div>
              <div className="border border-[#2d4a6f] rounded-lg overflow-hidden">
                <MenuBar editor={editor} />
                <EditorContent 
                  editor={editor} 
                  className={`bg-[#0a1628] transition-all duration-300 ${editorExpanded ? 'min-h-[500px] [&_.ProseMirror]:min-h-[500px]' : 'min-h-[200px] [&_.ProseMirror]:min-h-[200px]'} [&_.ProseMirror]:p-4 [&_.ProseMirror]:text-white [&_.ProseMirror]:focus:outline-none [&_.ProseMirror_p]:my-2 [&_.ProseMirror_ul]:list-disc [&_.ProseMirror_ul]:pl-6 [&_.ProseMirror_ol]:list-decimal [&_.ProseMirror_ol]:pl-6 [&_.ProseMirror_a]:text-blue-400 [&_.ProseMirror_a]:underline [&_.ProseMirror_img]:max-w-full [&_.ProseMirror_img]:h-auto [&_.ProseMirror_img]:rounded-lg`}
                />
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="flex items-center gap-2 px-4 py-2 bg-[#0a1628] border border-[#2d4a6f] rounded-lg text-gray-400 hover:text-white hover:border-blue-500/50 transition-colors"
              >
                <Eye className="w-4 h-4" />
                {showPreview ? 'Hide' : 'Preview'}
              </button>
              <button
                onClick={handleSendNewsletter}
                disabled={sending || !subject.trim()}
                className="flex-1 flex items-center justify-center gap-2 px-6 py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-medium rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {sending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Send to {stats.active} subscribers
                  </>
                )}
              </button>
            </div>

            {showPreview && editor && (
              <div className="p-4 bg-white rounded-lg">
                <div dangerouslySetInnerHTML={{ __html: getContent() }} />
              </div>
            )}

            {result && (
              <div className={`flex items-center gap-3 p-4 rounded-lg ${
                result.success 
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
                  : 'bg-red-500/20 text-red-400 border border-red-500/30'
              }`}>
                {result.success ? (
                  <CheckCircle className="w-5 h-5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                )}
                <span>{result.message}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewsletterManager;
