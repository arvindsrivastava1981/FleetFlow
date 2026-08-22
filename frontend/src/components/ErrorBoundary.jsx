import { Component } from "react";

// Audit E-2: catch render-time crashes inside page content and show a
// recoverable UI instead of a white screen. "Try again" resets the boundary
// state (re-rendering children); "Reload" is the nuclear option.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Surface for debugging; wire to an error-reporting sink later if needed.
    console.error("[ErrorBoundary]", error, info?.componentStack);
  }

  render() {
    if (this.state.error) {
      const message = String(
        this.state.error?.message || this.state.error || "Unknown error"
      );
      return (
        <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 px-4 text-center">
          <p className="text-4xl">💥</p>
          <h1 className="text-lg font-bold text-ink-900">Something went wrong</h1>
          <p className="max-w-md text-sm text-ink-500">{message}</p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={() => this.setState({ error: null })}
              className="btn-primary btn-sm"
            >
              Try again
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="btn-secondary btn-sm"
            >
              Reload page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
