import { lazy, Suspense } from "react";
import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";

// Audit E-3: route-level code splitting — every page is its own chunk, so the
// initial bundle only carries the shell + the route being visited.
const LoginPage = lazy(() => import("./pages/index.jsx"));
const DashboardPage = lazy(() => import("./pages/Dashboard.jsx"));
const TripsPage = lazy(() => import("./pages/Trips.jsx"));
const TripDetailPage = lazy(() => import("./pages/TripDetail.jsx"));
const NewTripPage = lazy(() => import("./pages/NewTrip.jsx"));
const ExpenseEntryPage = lazy(() => import("./pages/ExpenseEntry.jsx"));
const BulkEntryPage = lazy(() => import("./pages/BulkEntry.jsx"));
const FleetsPage = lazy(() => import("./pages/admin/Fleets.jsx"));
const UsersPage = lazy(() => import("./pages/admin/Users.jsx"));
const VehiclesPage = lazy(() => import("./pages/admin/Vehicles.jsx"));
const BenchmarksPage = lazy(() => import("./pages/admin/Benchmarks.jsx"));
const OnboardFirmPage = lazy(() => import("./pages/admin/OnboardFirm.jsx"));
const OnboardingPage = lazy(() => import("./pages/Onboarding.jsx"));
const AnalyticsPage = lazy(() => import("./pages/admin/Analytics.jsx"));
const ErrorLogsPage = lazy(() => import("./pages/admin/ErrorLogs.jsx"));
const SubscriptionPage = lazy(() => import("./pages/Billing.jsx"));
const SettledTripsPage = lazy(() => import("./pages/SettledTrips.jsx"));
const ChangePasswordPage = lazy(() => import("./pages/ChangePassword.jsx"));
const DriversPage = lazy(() => import("./pages/Drivers.jsx"));
const DriverSalaryPage = lazy(() => import("./pages/DriverSalary.jsx"));
const TripWhatsAppPage = lazy(() => import("./pages/TripWhatsApp.jsx"));
const NotFoundPage = lazy(() => import("./pages/NotFound.jsx"));
const Layout = lazy(() => import("./components/Layout.jsx"));

function SuspenseShell({ children }) {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-screen items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <div className="h-9 w-9 animate-spin rounded-full border-4 border-ink-200 border-t-brand-600" />
            <p className="text-sm text-ink-500">Loading…</p>
          </div>
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading)
    return (
      <div className="flex min-h-screen items-center justify-center bg-ink-50">
        <div className="flex flex-col items-center gap-3">
          <div className="h-9 w-9 animate-spin rounded-full border-4 border-ink-200 border-t-brand-600" />
          <p className="text-sm text-ink-500">Loading VahanKhata…</p>
        </div>
      </div>
    );
  if (!user) return <Navigate to="/" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  // Self-serve onboarding gate: a trip_manager with no fleet (e.g. fresh
  // social sign-up) must create their firm before using the app. super_admin
  // is fleetless by design and drivers are always bound by their manager.
  if (
    user.role === "trip_manager" &&
    !user.fleet_id &&
    location.pathname !== "/onboarding"
  ) {
    return <Navigate to="/onboarding" replace />;
  }
  return children;
}

export default function App() {
  const { user } = useAuth();
  return (
    <SuspenseShell>
      <Routes>
      {/* Login is the default entry point of the app SPA. */}
      <Route
        path="/"
        element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />}
      />
      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <Layout>
              <DashboardPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <TripsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips/:tripCode"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <TripDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips/:tripCode/log"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin", "driver"]}>
            <Layout>
              <ExpenseEntryPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips/:tripCode/bulk"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <BulkEntryPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/trips/new"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <NewTripPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp/:tripCode"
        element={
          <ProtectedRoute>
            <Layout>
              <TripWhatsAppPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp"
        element={
          <ProtectedRoute>
            <Layout>
              <TripWhatsAppPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settlements"
        element={
          <ProtectedRoute>
            <Layout>
              <SettledTripsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/driver-salary"
        element={
          <ProtectedRoute roles={["driver"]}>
            <Layout>
              <DriverSalaryPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/drivers"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <DriversPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/change-password"
        element={
          <ProtectedRoute>
            <Layout>
              <ChangePasswordPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/subscription"
        element={
          <ProtectedRoute roles={["trip_manager"]}>
            <Layout>
              <SubscriptionPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route path="/billing" element={<Navigate to="/subscription" replace />} />
      <Route
        path="/fleets"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <FleetsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/analytics"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <AnalyticsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/error-logs"
        element={
          <ProtectedRoute roles={["super_admin"]}>
            <Layout>
              <ErrorLogsPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/onboard"
        element={
          <ProtectedRoute roles={["super_admin"]}>
            <Layout>
              <OnboardFirmPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Self-serve firm setup for fleet-less users (social sign-ups). No
          Layout — it's a standalone modal-style page like the login screen. */}
      <Route
        path="/onboarding"
        element={
          <ProtectedRoute roles={["trip_manager"]}>
            <OnboardingPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/users"
        element={
          <ProtectedRoute roles={["super_admin"]}>
            <Layout>
              <UsersPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/vehicles"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <VehiclesPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/benchmarks"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <BenchmarksPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      {/* Catch-all: unknown SPA URLs render a friendly 404 (audit E-1). */}
      <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </SuspenseShell>
  );
}