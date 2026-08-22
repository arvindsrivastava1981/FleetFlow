import { Link } from "react-router-dom";

// Bare-bones 404 for unknown SPA URLs (audit E-1). Intentionally NOT wrapped
// in ProtectedRoute/Layout so anonymous deep-links to stale paths get a
// friendly page instead of a blank pane.
export default function NotFound() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-2 text-center">
      <p className="text-6xl font-black text-ink-200">404</p>
      <h1 className="text-lg font-bold text-ink-900">Page not found</h1>
      <p className="text-sm text-ink-500">
        The page you are looking for doesn&apos;t exist or was moved.
      </p>
      <Link to="/dashboard" className="btn-primary mt-3">
        Back to Dashboard
      </Link>
    </div>
  );
}
