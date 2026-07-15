import { configureStore } from '@reduxjs/toolkit';
import { hcpReducer, interactionReducer, agentReducer, uiReducer } from './slices';

const store = configureStore({
  reducer: {
    hcp: hcpReducer,
    interaction: interactionReducer,
    agent: agentReducer,
    ui: uiReducer,
  },
});

export default store;
