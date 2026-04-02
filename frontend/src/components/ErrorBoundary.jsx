import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("ErrorBoundary caught an error", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '50px', textAlign: 'center', color: '#ff4500' }}>
          <h2>Something went wrong.</h2>
          <p>The application encountered an unexpected error.</p>
          <button className="btn" onClick={() => window.location.href = '/'}>Return Home</button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
