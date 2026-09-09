import React from 'react';

interface ErrorState { error: Error | null }

export class ErrorBoundary extends React.Component<{ children: React.ReactNode }, ErrorState> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[Polaris] React Error Boundary caught:', error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          position: 'fixed', inset: 0, background: '#040810',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          fontFamily: 'monospace', color: '#ff4444', padding: 32,
        }}>
          <div style={{ fontSize: 28, marginBottom: 16 }}>⚠️ Runtime Error</div>
          <div style={{ fontSize: 14, color: '#ff6666', marginBottom: 12 }}>
            {this.state.error.message}
          </div>
          <pre style={{
            background: '#0a1222', padding: 16, borderRadius: 8,
            fontSize: 11, color: '#8ab4cc', maxWidth: '80vw', overflowX: 'auto',
            whiteSpace: 'pre-wrap', border: '1px solid rgba(0,229,255,0.15)',
          }}>
            {this.state.error.stack}
          </pre>
          <button
            onClick={() => this.setState({ error: null })}
            style={{
              marginTop: 16, padding: '8px 24px', background: 'rgba(0,229,255,0.15)',
              border: '1px solid #00e5ff', color: '#00e5ff', borderRadius: 8,
              cursor: 'pointer', fontSize: 14,
            }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
