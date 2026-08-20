import { Routes, Route, Navigate, Link } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import LoginPage from "./pages/index.jsx";
import DashboardPage from "./pages/Dashboard.jsx";
import TripsPage from "./pages/Trips.jsx";
import TripDetailPage from "./pages/TripDetail.jsx";
import NewTripPage from "./pages/NewTrip.jsx";
import ExpensesPage from "./pages/Expenses.jsx";
import FleetsPage from "./pages/admin/Fleets.jsx";
import UsersPage from "./pages/admin/Users.jsx";
import VehiclesPage from "./pages/admin/Vehicles.jsx";
import BenchmarksPage from "./pages/admin/Benchmarks.jsx";
import OnboardFirmPage from "./pages/admin/OnboardFirm.jsx";
import BillingPage from "./pages/Billing.jsx";
import RuleEnginePage from "./pages/RuleEngine.jsx";
import SettledTripsPage from "./pages/SettledTrips.jsx";
import ChangePasswordPage from "./pages/ChangePassword.jsx";
import DriversPage from "./pages/Drivers.jsx";
import DriverSalaryPage from "./pages/DriverSalary.jsx";
import ReportsPage from "./pages/Reports.jsx";
import DriverWhatsAppPage from "./pages/DriverWhatsApp.jsx";
import ManagerWhatsAppPage from "./pages/ManagerWhatsApp.jsx";
import Layout from "./components/Layout.jsx";

function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();
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
  return children;
}

export default function App() {
  const { user } = useAuth();
  return (
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
        path="/expenses"
        element={
          <ProtectedRoute>
            <Layout>
              <ExpensesPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp-driver"
        element={
          <ProtectedRoute roles={["driver"]}>
            <Layout>
              <DriverWhatsAppPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/whatsapp-manager"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <ManagerWhatsAppPage />
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
        path="/reports"
        element={
          <ProtectedRoute roles={["driver"]}>
            <Layout>
              <ReportsPage />
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
        path="/billing"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <BillingPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/rule-engine"
        element={
          <ProtectedRoute roles={["trip_manager", "super_admin"]}>
            <Layout>
              <RuleEnginePage />
            </Layout>
          </ProtectedRoute>
        }
      />
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
        path="/onboard"
        element={
          <ProtectedRoute roles={["super_admin"]}>
            <Layout>
              <OnboardFirmPage />
            </Layout>
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
          <ProtectedRoute roles={["super_admin"]}>
            <Layout>
              <BenchmarksPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route path="/admin" element={<Navigate to="/dashboard" replace />} />
      <Route path="/manager" element={<Navigate to="/dashboard" replace />} />
      <Route path="/driver" element={<Navigate to="/dashboard" replace />} />      
    </Routes>
  );
}