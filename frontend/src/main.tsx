import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { ErrorBoundary } from './ErrorBoundary';
import './index.css';

// ── Cesium Ion token (optional – if blank/placeholder, OSM free imagery used) ─
import * as Cesium from 'cesium';
const cesiumToken = import.meta.env.VITE_CESIUM_TOKEN;
if (cesiumToken && cesiumToken !== 'your_cesium_ion_access_token' && cesiumToken.length > 20) {
  Cesium.Ion.defaultAccessToken = cesiumToken;
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </ErrorBoundary>
);
