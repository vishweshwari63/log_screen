import { createSlice } from '@reduxjs/toolkit';

// --- HCP Slice ---
const hcpSlice = createSlice({
  name: 'hcp',
  initialState: {
    list: [],
    selectedHcp: null,
    searchQuery: '',
    loading: false,
    error: null,
  },
  reducers: {
    setHcps: (state, action) => { state.list = action.payload; },
    setSelectedHcp: (state, action) => { state.selectedHcp = action.payload; },
    setSearchQuery: (state, action) => { state.searchQuery = action.payload; },
    setHcpLoading: (state, action) => { state.loading = action.payload; },
    setHcpError: (state, action) => { state.error = action.payload; },
  }
});

// --- Interaction Slice ---
const interactionSlice = createSlice({
  name: 'interaction',
  initialState: {
    draft: {
      hcp_id: null,
      rep_id: 'rep_999',
      discussion_topics: [],
      products_discussed: [],
      samples_distributed: [],
      competitors_mentioned: [],
      objections: '',
      outcome: '',
      consent_given: true,
      raw_text: '',
      mode: 'structured' // 'chat' or 'structured'
    },
    timeline: [],
    submitting: false,
    error: null
  },
  reducers: {
    updateDraftField: (state, action) => {
      const { field, value } = action.payload;
      state.draft[field] = value;
    },
    resetDraft: (state) => {
      const hcpId = state.draft.hcp_id;
      state.draft = {
        hcp_id: hcpId,
        rep_id: 'rep_999',
        discussion_topics: [],
        products_discussed: [],
        samples_distributed: [],
        competitors_mentioned: [],
        objections: '',
        outcome: '',
        consent_given: true,
        raw_text: '',
        mode: state.draft.mode
      };
    },
    setTimeline: (state, action) => { state.timeline = action.payload; },
    setSubmitting: (state, action) => { state.submitting = action.payload; },
    setInteractionError: (state, action) => { state.error = action.payload; },
  }
});

// --- Agent Slice ---
const agentSlice = createSlice({
  name: 'agent',
  initialState: {
    currentNode: null,
    nodeTrace: [],
    toolResults: {},
    confidence: null,
    sentiment: null,
    aiSummary: '',
    complianceReport: { risk_flags: [], severity: 'NONE', detailed_analysis: '' },
    isStreaming: false,
    traceHistory: []
  },
  reducers: {
    startAgentStream: (state) => {
      state.isStreaming = true;
      state.currentNode = 'entry';
      state.nodeTrace = ['entry'];
      state.toolResults = {};
      state.complianceReport = { risk_flags: [], severity: 'NONE', detailed_analysis: '' };
      state.aiSummary = '';
      state.sentiment = null;
      state.confidence = null;
    },
    updateAgentStep: (state, action) => {
      const { node, summary, compliance_report, selected_tool, plan, tool_output, sentiment, confidence } = action.payload;
      state.currentNode = node;
      if (!state.nodeTrace.includes(node)) {
        state.nodeTrace.push(node);
      }
      if (summary) state.aiSummary = summary;
      if (compliance_report) state.complianceReport = compliance_report;
      if (tool_output) {
        state.toolResults = tool_output;
        if (tool_output.sentiment) state.sentiment = tool_output.sentiment;
        if (tool_output.sentiment_confidence) state.confidence = tool_output.sentiment_confidence;
        if (tool_output.ai_summary) state.aiSummary = tool_output.ai_summary;
      }
    },
    stopAgentStream: (state) => {
      state.isStreaming = false;
    },
    setTraceHistory: (state, action) => {
      state.traceHistory = action.payload;
    }
  }
});

// --- UI Slice ---
const uiSlice = createSlice({
  name: 'ui',
  initialState: {
    activeTab: 'Form', // 'Form', 'Chat', 'Timeline', 'Insights'
  },
  reducers: {
    setActiveTab: (state, action) => { state.activeTab = action.payload; }
  }
});

// Export reducers
export const hcpReducer = hcpSlice.reducer;
export const interactionReducer = interactionSlice.reducer;
export const agentReducer = agentSlice.reducer;
export const uiReducer = uiSlice.reducer;

// Export actions
export const { setHcps, setSelectedHcp, setSearchQuery, setHcpLoading, setHcpError } = hcpSlice.actions;
export const { updateDraftField, resetDraft, setTimeline, setSubmitting, setInteractionError } = interactionSlice.actions;
export const { startAgentStream, updateAgentStep, stopAgentStream, setTraceHistory } = agentSlice.actions;
export const { setActiveTab } = uiSlice.actions;
