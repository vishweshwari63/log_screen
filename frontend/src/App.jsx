import React, { useEffect, useState, useRef } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { 
  User, Activity, FileText, MessageSquare, Clock, ShieldAlert, 
  Sparkles, Plus, Search, Mail, MapPin, AlertTriangle, 
  CheckCircle2, Loader2, ArrowRight, ShieldCheck, Heart, Award,
  Package, FlaskConical, Target, AlertCircle, CalendarRange, 
  Sun, Moon, ChevronDown, ChevronUp, FileCode, CheckSquare, Sparkle, BrainCircuit
} from 'lucide-react';
import { 
  setHcps, setSelectedHcp, setSearchQuery, setHcpLoading,
  updateDraftField, resetDraft, setTimeline, setSubmitting,
  startAgentStream, updateAgentStep, stopAgentStream, setTraceHistory,
  setActiveTab
} from './store/slices';

const BACKEND_URL = 'http://localhost:8000';

export default function App() {
  const dispatch = useDispatch();
  
  // Selectors
  const { list: hcpList, selectedHcp, searchQuery, loading: hcpLoading } = useSelector(state => state.hcp);
  const { draft, timeline, submitting } = useSelector(state => state.interaction);
  const { currentNode, nodeTrace, toolResults, confidence, sentiment, aiSummary, complianceReport, isStreaming } = useSelector(state => state.agent);
  const { activeTab } = useSelector(state => state.ui);

  // Theme support
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'dark';
  });

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    localStorage.setItem('theme', theme);
  }, [theme]);

  // Local state
  const [chatInput, setChatInput] = useState('');
  const [chatMessages, setChatMessages] = useState([
    { sender: 'AI', text: 'Hello! I am your AI Copilot. Describe your detailing session here, or fill out the structured form in the workspace. I will scan compliance, calculate sentiments, draft follow-up templates, and synchronize this to the database.' }
  ]);
  
  const [emailDraft, setEmailDraft] = useState('');
  const [loadingEmail, setLoadingEmail] = useState(false);
  const [traceExpanded, setTraceExpanded] = useState(true);

  // Form chip buffers
  const [topicInput, setTopicInput] = useState('');
  const [prodInput, setProdInput] = useState('');
  const [sampleInput, setSampleInput] = useState('');
  const [compInput, setCompInput] = useState('');

  const chatEndRef = useRef(null);

  // Fetch doctors on mount
  useEffect(() => {
    fetchHcps();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  const fetchHcps = async (query = '') => {
    dispatch(setHcpLoading(true));
    try {
      const res = await fetch(`${BACKEND_URL}/api/hcps?query=${encodeURIComponent(query || 'Dr')}`);
      if (res.ok) {
        const data = await res.json();
        dispatch(setHcps(data.results || []));
        if (data.results && data.results.length > 0 && !selectedHcp) {
          selectHcp(data.results[0]);
        }
      }
    } catch (err) {
      console.error("Failed to fetch HCPs:", err);
    } finally {
      dispatch(setHcpLoading(false));
    }
  };

  const selectHcp = async (hcp) => {
    dispatch(setSelectedHcp(hcp));
    dispatch(updateDraftField({ field: 'hcp_id', value: hcp.id }));
    // Fetch historical interaction records
    try {
      const res = await fetch(`${BACKEND_URL}/api/interactions/${hcp.id}/agent-trace`);
      if (res.ok) {
        const data = await res.json();
        dispatch(setTimeline(data.trace || []));
      } else {
        dispatch(setTimeline([]));
      }
    } catch (err) {
      dispatch(setTimeline([]));
      console.error(err);
    }
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const handleFormFieldChange = (field, value) => {
    dispatch(updateDraftField({ field, value }));
  };

  const handleAddChip = (field, value) => {
    if (!value.trim()) return;
    const currentList = draft[field] || [];
    if (!currentList.includes(value)) {
      handleFormFieldChange(field, [...currentList, value]);
    }
  };

  const handleRemoveChip = (field, index) => {
    const currentList = draft[field] || [];
    const updated = currentList.filter((_, i) => i !== index);
    handleFormFieldChange(field, updated);
  };

  // SSE Stream runner
  const runAgentWorkflow = (userRequestText, mode) => {
    dispatch(startAgentStream());
    dispatch(setSubmitting(true));

    const encodedReq = encodeURIComponent(userRequestText);
    const hcpId = selectedHcp?.id || 1;
    const sseUrl = `${BACKEND_URL}/api/interactions/stream?user_request=${encodedReq}&hcp_id=${hcpId}&rep_id=rep_999&mode=${mode}`;

    const eventSource = new EventSource(sseUrl);

    eventSource.addEventListener('node', (e) => {
      const data = JSON.parse(e.data);
      dispatch(updateAgentStep(data));
    });

    eventSource.addEventListener('complete', () => {
      eventSource.close();
      dispatch(stopAgentStream());
      dispatch(setSubmitting(false));
      if (selectedHcp) {
        selectHcp(selectedHcp);
      }
    });

    eventSource.addEventListener('error', (err) => {
      console.error("SSE Connection issue:", err);
      eventSource.close();
      dispatch(stopAgentStream());
      dispatch(setSubmitting(false));
    });
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!selectedHcp) return;
    const requestSummary = `Log detailed structured CRM interaction for Dr. ${selectedHcp.name}. Products: ${draft.products_discussed.join(', ')}. Topics: ${draft.discussion_topics.join(', ')}. Samples: ${draft.samples_distributed.join(', ')}. Competitors: ${draft.competitors_mentioned.join(', ')}. Objections: ${draft.objections || 'None'}. Outcome: ${draft.outcome}.`;
    runAgentWorkflow(requestSummary, 'structured');
  };

  const handleSendChat = (e) => {
    e.preventDefault();
    if (!chatInput.trim() || !selectedHcp) return;

    const query = chatInput;
    setChatMessages(prev => [...prev, { sender: 'User', text: query }]);
    setChatInput('');
    setChatMessages(prev => [...prev, { sender: 'AI', text: 'Processing detailing query through LangGraph agents...' }]);

    handleFormFieldChange('raw_text', query);
    handleFormFieldChange('mode', 'chat');

    runAgentWorkflow(query, 'chat');
  };

  const triggerEmailCreation = async (intId) => {
    if (!intId) return;
    setLoadingEmail(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/interactions/${intId}/followup-email`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setEmailDraft(data.email_body || 'Email could not be generated.');
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingEmail(false);
    }
  };

  // Avatar helper
  const getAvatarInitials = (name) => {
    if (!name) return 'DR';
    const splitArr = name.replace('Dr. ', '').split(' ');
    if (splitArr.length >= 2) return `${splitArr[0][0]}${splitArr[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-[#0B1220] text-[#0F172A] dark:text-[#F8FAFC] flex flex-col font-sans transition-colors duration-200">
      
      {/* SaaS Header */}
      <header className="border-b border-[#E2E8F0] dark:border-[#2D3748] bg-white dark:bg-[#111827] sticky top-0 z-50 px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="bg-[#2563EB] dark:bg-[#3B82F6] text-white p-2.5 rounded-xl shadow-md flex items-center justify-center">
            <BrainCircuit className="w-5.5 h-5.5" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">CopilotCRM</h1>
            <p className="text-xs text-[#64748B] dark:text-[#94A3B8] font-medium">Enterprise Pharmaceutical CRM</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5 px-3 py-1 bg-[#E2E8F0] dark:bg-[#1F2937] text-xs font-semibold rounded-full border border-transparent dark:border-[#2D3748]">
            <span className="w-2.5 h-2.5 rounded-full bg-[#16A34A] dark:bg-[#22C55E] animate-pulse"></span>
            Agent Ready
          </span>

          <button
            onClick={toggleTheme}
            className="p-2 rounded-xl border border-[#E2E8F0] dark:border-[#2D3748] hover:bg-[#F1F5F9] dark:hover:bg-[#1E293B] transition-colors"
            title="Toggle theme mode"
          >
            {theme === 'dark' ? <Sun className="w-4 h-4 text-[#14B8A6]" /> : <Moon className="w-4 h-4 text-[#2563EB]" />}
          </button>
        </div>
      </header>

      {/* 3-Column Workspace */}
      <main className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-6 max-w-[1600px] w-full mx-auto">
        
        {/* COLUMN 1: LEFT SIDEBAR (Physician Details & Switcher) */}
        <section className="lg:col-span-3 flex flex-col gap-6 w-full lg:max-w-[320px]">
          
          {/* Card: Physician Search */}
          <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#2D3748] rounded-2xl p-5 shadow-soft dark:shadow-soft-dark flex flex-col gap-3">
            <h2 className="text-sm font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8]">Target List</h2>
            <div className="relative">
              <Search className="absolute left-3 top-3 w-4.5 h-4.5 text-[#64748B] dark:text-[#94A3B8]" />
              <input
                type="text"
                placeholder="Search specialists..."
                className="w-full bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl pl-10 pr-4 h-11 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50 dark:focus:ring-[#3B82F6]/50 placeholder:text-[#64748B] dark:placeholder:text-[#94A3B8] transition-colors"
                value={searchQuery}
                onChange={e => dispatch(setSearchQuery(e.target.value))}
                onKeyDown={(e) => e.key === 'Enter' && fetchHcps(searchQuery)}
              />
            </div>
            <button
              onClick={() => fetchHcps(searchQuery)}
              className="w-full bg-[#2563EB] dark:bg-[#3B82F6] hover:bg-opacity-90 text-white font-semibold h-11 rounded-xl text-xs tracking-wider transition-all uppercase"
            >
              Analyze Directory
            </button>
          </div>

          {/* Card: Physicians List Container */}
          <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#2D3748] rounded-2xl p-5 shadow-soft dark:shadow-soft-dark flex-1 flex flex-col gap-3 overflow-y-auto max-h-[620px]">
            <span className="text-xs font-bold text-[#64748B] dark:text-[#94A3B8] uppercase tracking-wider">HCP Contacts ({hcpList.length})</span>
            {hcpLoading ? (
              <div className="flex justify-center items-center py-12">
                <Loader2 className="w-8 h-8 animate-spin text-[#2563EB] dark:text-[#3B82F6]" />
              </div>
            ) : (
              <div className="flex flex-col gap-3">
                {hcpList.map(h => (
                  <button
                    key={h.id}
                    onClick={() => selectHcp(h)}
                    className={`w-full text-left p-4 rounded-xl border transition-all flex items-start gap-3.5 relative ${
                      selectedHcp?.id === h.id 
                        ? 'border-[#2563EB] bg-[#2563EB]/5 dark:border-[#3B82F6] dark:bg-[#3B82F6]/5 ring-1 ring-[#2563EB]/20 dark:ring-[#3B82F6]/20' 
                        : 'border-[#E2E8F0] dark:border-[#2D3748] hover:bg-[#F1F5F9] dark:hover:bg-[#1E293B]'
                    }`}
                  >
                    {/* Specialty Status check dot */}
                    <div className="absolute top-4 right-4 w-2 h-2 rounded-full bg-[#16A34A] dark:bg-[#22C55E]" title="Active interaction recommended"></div>

                    {/* Designer Initials Avatar */}
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-[#2563EB] to-[#0EA5E9] dark:from-[#3B82F6] to-[#14B8A6] text-white flex items-center justify-center font-bold text-xs shadow-sm">
                      {getAvatarInitials(h.name)}
                    </div>
                    
                    <div className="flex-1 min-w-0 flex flex-col gap-1">
                      <h4 className="font-bold text-sm truncate">{h.name}</h4>
                      <p className="text-xs text-[#64748B] dark:text-[#94A3B8] font-medium flex items-center gap-1.5"><MapPin className="w-3.5 h-3.5" /> {h.hospital}</p>
                      
                      <div className="flex flex-wrap gap-1 mt-1">
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-[#F1F5F9] dark:bg-[#1F2937] text-[#64748B] dark:text-[#94A3B8]">{h.specialization}</span>
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-[#16A34A] dark:text-[#22C55E]">Score: {h.relationship_score.toFixed(1)}</span>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* COLUMN 2: CENTER WORKSPACE (Tabs, Form controls) */}
        <section className="lg:col-span-5 flex flex-col gap-6">
          <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#2D3748] rounded-2xl p-6 shadow-soft dark:shadow-soft-dark flex flex-col gap-6 flex-1">
            
            {/* Header Tabs */}
            <div className="bg-[#F8FAFC] dark:bg-[#1E293B] p-1 rounded-xl flex items-center gap-1 border border-[#E2E8F0] dark:border-[#2D3748]">
              {[
                { id: 'Form', label: 'Form Entry', icon: FileText },
                { id: 'Chat', label: 'AI Chat Detailing', icon: MessageSquare },
                { id: 'Timeline', label: 'CRM Timeline', icon: Clock }
              ].map(t => {
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    onClick={() => dispatch(setActiveTab(t.id))}
                    className={`flex-1 h-10 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-all ${
                      activeTab === t.id
                        ? 'bg-white dark:bg-[#111827] text-[#2563EB] dark:text-[#3B82F6] shadow-sm'
                        : 'text-[#64748B] dark:text-[#94A3B8] hover:text-[#0F172A] dark:hover:text-white'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {t.label}
                  </button>
                );
              })}
            </div>

            {/* TAB: Form Logging */}
            {activeTab === 'Form' && (
              <form onSubmit={handleFormSubmit} className="flex-1 flex flex-col gap-5 overflow-y-auto max-h-[620px] pr-1">
                
                {/* Visual Section: Products Discussed */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-blue-500/10 text-[#2563EB] dark:text-[#3B82F6] rounded-lg">
                      <Package className="w-4 h-4" />
                    </div>
                    <label className="text-xs font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8]">Products Discussed</label>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="E.g. Crestor 10mg..."
                      className="flex-1 bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl px-4 h-11 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50"
                      value={prodInput}
                      onChange={e => setProdInput(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => { handleAddChip('products_discussed', prodInput); setProdInput(''); }}
                      className="px-4 bg-[#F1F5F9] dark:bg-[#1F2937] hover:bg-opacity-80 rounded-xl text-xs font-bold border border-[#E2E8F0] dark:border-[#2D3748]"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {draft.products_discussed.map((p, idx) => (
                      <span key={idx} className="bg-[#2563EB]/10 text-[#2563EB] dark:text-[#3B82F6] dark:bg-[#3B82F6]/10 text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                        {p}
                        <button type="button" onClick={() => handleRemoveChip('products_discussed', idx)} className="hover:text-red-500">×</button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Visual Section: Discussion Topics */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-emerald-500/10 text-[#16A34A] dark:text-[#22C55E] rounded-lg">
                      <FileText className="w-4 h-4" />
                    </div>
                    <label className="text-xs font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8]">Discussion Topics</label>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="E.g. clinical efficacy trials..."
                      className="flex-1 bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl px-4 h-11 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50"
                      value={topicInput}
                      onChange={e => setTopicInput(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => { handleAddChip('discussion_topics', topicInput); setTopicInput(''); }}
                      className="px-4 bg-[#F1F5F9] dark:bg-[#1F2937] hover:bg-opacity-80 rounded-xl text-xs font-bold border border-[#E2E8F0] dark:border-[#2D3748]"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {draft.discussion_topics.map((t, idx) => (
                      <span key={idx} className="bg-emerald-500/10 text-[#16A34A] dark:text-[#22C55E] text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                        {t}
                        <button type="button" onClick={() => handleRemoveChip('discussion_topics', idx)} className="hover:text-red-500">×</button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Visual Section: Samples Distributed */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-indigo-500/10 text-[#6366F1] rounded-lg">
                      <FlaskConical className="w-4 h-4" />
                    </div>
                    <label className="text-xs font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8]">Samples Distributed</label>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="E.g. Pack of 5 trial kits..."
                      className="flex-1 bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl px-4 h-11 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50"
                      value={sampleInput}
                      onChange={e => setSampleInput(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => { handleAddChip('samples_distributed', sampleInput); setSampleInput(''); }}
                      className="px-4 bg-[#F1F5F9] dark:bg-[#1F2937] hover:bg-opacity-80 rounded-xl text-xs font-bold border border-[#E2E8F0] dark:border-[#2D3748]"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {draft.samples_distributed.map((s, idx) => (
                      <span key={idx} className="bg-indigo-500/10 text-[#6366F1] text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                        {s}
                        <button type="button" onClick={() => handleRemoveChip('samples_distributed', idx)} className="hover:text-red-500">×</button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Visual Section: Competitors Mentioned */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-rose-500/10 text-[#EF4444] rounded-lg">
                      <Target className="w-4 h-4" />
                    </div>
                    <label className="text-xs font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8]">Competitors Mentioned</label>
                  </div>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      placeholder="E.g. Lipitor, Crestor..."
                      className="flex-1 bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl px-4 h-11 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50"
                      value={compInput}
                      onChange={e => setCompInput(e.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => { handleAddChip('competitors_mentioned', compInput); setCompInput(''); }}
                      className="px-4 bg-[#F1F5F9] dark:bg-[#1F2937] hover:bg-opacity-80 rounded-xl text-xs font-bold border border-[#E2E8F0] dark:border-[#2D3748]"
                    >
                      Add
                    </button>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {draft.competitors_mentioned.map((c, idx) => (
                      <span key={idx} className="bg-rose-500/10 text-[#EF4444] text-xs font-semibold px-2.5 py-1 rounded-lg flex items-center gap-1.5">
                        {c}
                        <button type="button" onClick={() => handleRemoveChip('competitors_mentioned', idx)} className="hover:text-red-500">×</button>
                      </span>
                    ))}
                  </div>
                </div>

                {/* Visual Section: Objections */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-amber-500/10 text-amber-505 text-amber-500 rounded-lg">
                      <AlertCircle className="w-4 h-4" />
                    </div>
                    <label className="text-xs font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8]">Objections Raised</label>
                  </div>
                  <textarea
                    className="w-full bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl p-4 text-sm h-28 focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50 placeholder:text-[#64748B]"
                    placeholder="Describe specific safety, dosage, or regulatory compliance objections raised..."
                    value={draft.objections}
                    onChange={e => handleFormFieldChange('objections', e.target.value)}
                  />
                </div>

                {/* Visual Section: Outcome */}
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 bg-blue-500/10 text-[#2563EB] rounded-lg">
                      <CheckCircle2 className="w-4 h-4" />
                    </div>
                    <label className="text-xs font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8]">Call Outcome</label>
                  </div>
                  <textarea
                    className="w-full bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl p-4 text-sm h-28 focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50 placeholder:text-[#64748B]"
                    placeholder="Summary of next actions, meetings, or trial commitments..."
                    value={draft.outcome}
                    onChange={e => handleFormFieldChange('outcome', e.target.value)}
                  />
                </div>

                {/* Consent checkbox and action */}
                <div className="border-t border-[#E2E8F0] dark:border-[#2D3748] pt-5 flex flex-col sm:flex-row items-center justify-between gap-4 mt-3">
                  <label className="flex items-center gap-2.5 text-xs text-[#64748B] dark:text-[#94A3B8] cursor-pointer">
                    <input
                      type="checkbox"
                      className="rounded border-[#E2E8F0] dark:border-[#2D3748] bg-[#F8FAFC] dark:bg-[#1F2937] text-[#2563EB] focus:ring-opacity-20"
                      checked={draft.consent_given}
                      onChange={e => handleFormFieldChange('consent_given', e.target.checked)}
                    />
                    Physician consent acquired (HIPAA compliance check)
                  </label>
                  <button
                    type="submit"
                    disabled={submitting || !selectedHcp}
                    className="bg-[#2563EB] dark:bg-[#3B82F6] hover:bg-opacity-95 text-white font-bold h-11 px-6 rounded-xl text-xs flex items-center justify-center gap-2 shadow-md transition-all uppercase tracking-wider disabled:opacity-50"
                  >
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                    Synchronize CRM
                  </button>
                </div>

              </form>
            )}

            {/* TAB: Chat transcription */}
            {activeTab === 'Chat' && (
              <div className="flex-1 flex flex-col h-[520px]">
                <div className="flex-1 overflow-y-auto mb-4 border border-[#E2E8F0] dark:border-[#2D3748] rounded-2xl p-5 flex flex-col gap-4 bg-[#F8FAFC] dark:bg-[#111827]">
                  {chatMessages.map((m, idx) => (
                    <div key={idx} className={`flex flex-col max-w-[85%] ${m.sender === 'User' ? 'self-end items-end' : 'self-start items-start'}`}>
                      <span className="text-[10px] font-bold text-[#64748B] dark:text-[#94A3B8] uppercase mb-0.5">{m.sender}</span>
                      <div className={`p-4 rounded-2xl text-sm leading-relaxed ${
                        m.sender === 'User' 
                          ? 'bg-[#2563EB] dark:bg-[#3B82F6] text-white shadow-sm rounded-tr-none' 
                          : 'bg-white dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] shadow-sm rounded-tl-none'
                      }`}>
                        {m.text}
                      </div>
                    </div>
                  ))}
                  <div ref={chatEndRef} />
                </div>

                <form onSubmit={handleSendChat} className="flex gap-2">
                  <input
                    type="text"
                    placeholder="Paste transcription text or write instructions..."
                    className="flex-1 bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl px-4 h-11 text-sm focus:outline-none focus:ring-2 focus:ring-[#2563EB]/50"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    disabled={submitting}
                  />
                  <button
                    type="submit"
                    disabled={submitting || !chatInput.trim()}
                    className="bg-[#2563EB] dark:bg-[#3B82F6] hover:bg-opacity-95 text-white font-bold h-11 px-5 rounded-xl text-xs uppercase"
                  >
                    Analyze
                  </button>
                </form>
              </div>
            )}

            {/* TAB: CRM Timeline */}
            {activeTab === 'Timeline' && (
              <div className="flex-1 overflow-y-auto max-h-[620px] pr-1 flex flex-col gap-4">
                <h3 className="text-sm font-bold text-[#64748B] dark:text-[#94A3B8] uppercase tracking-wide">Historical Detailing Runs</h3>
                {timeline.length === 0 ? (
                  <p className="text-xs text-[#64748B] dark:text-[#94A3B8] text-center py-12">No past records stored for this doctor.</p>
                ) : (
                  <div className="flex flex-col gap-4 relative pl-4 border-l border-[#E2E8F0] dark:border-[#2D3748]">
                    {timeline.map((item, idx) => (
                      <div key={idx} className="relative flex flex-col gap-2.5 bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] rounded-xl p-4 shadow-sm">
                        <div className="absolute -left-[21px] top-6 w-2.5 h-2.5 rounded-full bg-[#2563EB] dark:bg-[#3B82F6] border-2 border-white dark:border-[#111827]"></div>
                        
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="text-xs font-bold text-[#0F172A] dark:text-white uppercase">{item.tool_name}</h4>
                            <span className="text-[10px] text-[#64748B] dark:text-[#94A3B8]">{item.created_at}</span>
                          </div>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                            item.status === 'SUCCESS' ? 'bg-[#16A34A]/10 text-[#16A34A] dark:text-[#22C55E]' : 'bg-[#DC2626]/10 text-[#DC2626] dark:text-[#EF4444]'
                          }`}>{item.status}</span>
                        </div>
                        <div className="text-xs text-[#64748B] dark:text-[#94A3B8] leading-relaxed pt-2 border-t border-[#E2E8F0] dark:border-[#2D3748]">
                          {item.output_payload?.summary && <p className="mb-1"><strong>Entity Summary:</strong> {item.output_payload.summary}</p>}
                          {item.output_payload?.updated_fields && <p><strong>Fields Changed:</strong> {item.output_payload.updated_fields.join(', ')}</p>}
                          <p className="text-[10px] text-[#64748B] dark:text-[#94A3B8] mt-2">Duration: {item.latency_ms}ms</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

          </div>
        </section>

        {/* COLUMN 3: RIGHT PANEL (AI Insights, Sentiment, Trace) */}
        <section className="lg:col-span-4 flex flex-col gap-6 w-full lg:max-w-[380px]">
          
          <div className="bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#2D3748] rounded-2xl p-6 shadow-soft dark:shadow-soft-dark flex flex-col gap-5 flex-1 overflow-y-auto max-h-[820px]">
            <h3 className="text-sm font-bold uppercase tracking-wider text-[#64748B] dark:text-[#94A3B8] flex items-center gap-2">
              <Sparkle className="w-4 h-4 text-[#0EA5E9] dark:text-[#14B8A6] animate-pulse" /> AI Insights Panel
            </h3>
            
            {/* Sentiment Badges */}
            {sentiment ? (
              <div className="bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] p-4 rounded-xl flex flex-col gap-3">
                <span className="text-[10px] font-bold text-[#64748B] dark:text-[#94A3B8] uppercase">Sentiment Diagnostic</span>
                <div className="flex justify-between items-center">
                  <span className={`text-xs font-bold uppercase px-3 py-1 rounded-full ${
                    sentiment === 'POSITIVE' ? 'bg-[#16A34A]/10 text-[#16A34A] dark:text-[#22C55E]' : 
                    sentiment === 'SKEPTICAL' ? 'bg-[#F59E0B]/10 text-[#F59E0B] dark:text-[#FBBF24]' : 
                    sentiment === 'NEGATIVE' ? 'bg-[#DC2626]/10 text-[#DC2626] dark:text-[#EF4444]' : 
                    'bg-[#E2E8F0] dark:bg-[#2D3748] text-[#64748B]'
                  }`}>{sentiment}</span>
                  <span className="text-xs font-bold text-[#64748B] dark:text-[#94A3B8]">Confidence: {Math.round((confidence || 0.85) * 100)}%</span>
                </div>
              </div>
            ) : (
              <div className="text-xs text-[#64748B] dark:text-[#94A3B8] py-2">No active sentiment calculated yet. Submit details to analyze.</div>
            )}

            {/* AI Summary */}
            {aiSummary && (
              <div className="bg-[#F8FAFC] dark:bg-[#1F2937] border border-[#E2E8F0] dark:border-[#2D3748] p-4 rounded-xl flex flex-col gap-2">
                <span className="text-[10px] font-bold text-[#64748B] dark:text-[#94A3B8] uppercase">Clinical Detailing Summary</span>
                <p className="text-xs leading-relaxed font-medium text-[#0F172A] dark:text-[#F8FAFC]">
                  {aiSummary}
                </p>
              </div>
            )}

            {/* Entity chips list */}
            {toolResults.products_discussed && (
              <div className="flex flex-col gap-2">
                <span className="text-[10.5px] font-bold text-[#64748B] dark:text-[#94A3B8] uppercase">Extracted Entity Chips</span>
                <div className="flex flex-wrap gap-1">
                  {toolResults.products_discussed.map((p, idx) => (
                    <span key={idx} className="bg-blue-500/10 text-[#2563EB] dark:text-[#3B82F6] text-[10px] px-2 py-0.5 rounded font-bold">Prod: {p}</span>
                  ))}
                  {toolResults.competitors_mentioned && toolResults.competitors_mentioned.map((c, idx) => (
                    <span key={idx} className="bg-rose-500/10 text-rose-503 text-[10px] px-2 py-0.5 rounded font-bold">Comp: {c}</span>
                  ))}
                </div>
              </div>
            )}

            {/* Compliance warning risks alerts */}
            {complianceReport.risk_flags && complianceReport.risk_flags.length > 0 ? (
              <div className={`p-4 rounded-xl border flex flex-col gap-2 bg-red-500/5 ${
                complianceReport.severity === 'HIGH' ? 'border-[#DC2626]/30 text-[#DC2626] dark:text-[#EF4444]' : 'border-[#F59E0B]/30 text-[#F59E0B] dark:text-[#FBBF24]'
              }`}>
                <div className="flex items-center gap-1.5 text-xs font-bold uppercase">
                  <ShieldAlert className="w-4.5 h-4.5" />
                  Compliance Flag: {complianceReport.severity}
                </div>
                <ul className="list-disc pl-4 text-[11px] flex flex-col gap-1 text-[#64748B] dark:text-[#94A3B8]">
                  {complianceReport.risk_flags.map((item, idx) => (
                    <li key={idx} className="leading-relaxed">{item}</li>
                  ))}
                </ul>
              </div>
            ) : (
              sentiment && (
                <div className="flex items-center gap-2 text-xs text-[#16A34A] dark:text-[#22C55E] bg-[#16A34A]/5 border border-[#16A34A]/20 p-3 rounded-lg">
                  <ShieldCheck className="w-5 h-5" />
                  Compliance assessment clear.
                </div>
              )
            )}

            {/* Follow-up Drafting Section */}
            {toolResults.interaction_id && (
              <div className="flex flex-col gap-2 mt-2">
                <button
                  type="button"
                  onClick={() => triggerEmailCreation(toolResults.interaction_id)}
                  disabled={loadingEmail}
                  className="w-full bg-[#2563EB] dark:bg-[#3B82F6] hover:bg-opacity-95 text-white font-bold h-11 rounded-xl text-xs flex items-center justify-center gap-2"
                >
                  {loadingEmail ? <Loader2 className="w-4 h-4 animate-spin" /> : <Mail className="w-4 h-4" />}
                  Assemble Follow-up Email
                </button>
                {emailDraft && (
                  <div className="bg-[#F8FAFC] dark:bg-[#1E293B] border border-[#E2E8F0] dark:border-[#2D3748] p-4.5 rounded-xl flex flex-col gap-2 shadow-inner">
                    <span className="text-[10px] font-bold text-[#64748B] dark:text-[#94A3B8] uppercase">Email Content Draft</span>
                    <pre className="text-xs p-2 rounded bg-white dark:bg-[#111827] border border-[#E2E8F0] dark:border-[#2D3748] text-[#0F172A] dark:text-[#F8FAFC] overflow-x-auto whitespace-pre-wrap font-mono uppercase-none">{emailDraft}</pre>
                  </div>
                )}
              </div>
            )}

            {/* Collapsible Tracer Section */}
            <div className="border-t border-[#E2E8F0] dark:border-[#2D3748] pt-4 mt-2">
              <button
                onClick={() => setTraceExpanded(!traceExpanded)}
                className="w-full flex items-center justify-between text-xs font-bold text-[#64748B] dark:text-[#94A3B8] uppercase py-1"
              >
                <span>LangGraph Execution Trace</span>
                {traceExpanded ? <ChevronUp className="w-4.5 h-4.5" /> : <ChevronDown className="w-4.5 h-4.5" />}
              </button>
              
              {traceExpanded && (
                <div className="flex flex-col gap-1.5 mt-3 pl-1">
                  {[
                    { name: 'understand_request', label: 'Understand Request' },
                    { name: 'plan', label: 'Execution Planner' },
                    { name: 'select_tool', label: 'Tool Dispatcher' },
                    { name: 'execute_tool', label: 'Exec Tool Node' },
                    { name: 'update_crm', label: 'CRM Sync DDL' },
                    { name: 'generate_summary', label: 'Write Context Summary' },
                    { name: 'save_data', label: 'Audit Trail Persistence' },
                    { name: 'complete', label: 'Complete Phase' }
                  ].map((s, idx) => {
                    const isVisited = nodeTrace.includes(s.name);
                    const isCurrent = currentNode === s.name;
                    
                    return (
                      <div key={idx} className="flex items-center justify-between text-[11px]">
                        <div className="flex items-center gap-2">
                          <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center font-bold text-[8px] border ${
                            isCurrent 
                              ? 'bg-[#3B82F6]/20 border-[#3B82F6] text-[#3B82F6] animate-pulse' 
                              : isVisited
                              ? 'bg-[#16A34A]/80 border-[#16A34A] text-white'
                              : 'border-[#E2E8F0] dark:border-[#2D3748]'
                          }`}>
                            {isVisited ? '✓' : idx + 1}
                          </div>
                          <span className={`${isCurrent ? 'text-[#2563EB] dark:text-[#3B82F6] font-bold' : isVisited ? 'text-[#0F172A] dark:text-[#F8FAFC]' : 'text-[#64748B] dark:text-[#94A3B8]'}`}>{s.label}</span>
                        </div>
                        {isCurrent && (
                          <span className="text-[8px] text-[#3B82F6] bg-[#3B82F6]/5 px-1 py-0.2 rounded border border-[#3B82F6]/25 animate-pulse uppercase">Active</span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
