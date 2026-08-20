import { Routes, Route, Navigate, Link } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import LoginPage from "./pages/Login.jsx";
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
import PublicLayout from "./public/PublicLayout.jsx";
import HomePage from "./public/pages/Home.jsx";
import AboutPage from "./public/pages/About.jsx";
import WhyUsPage from "./public/pages/WhyUs.jsx";
import FeaturesPage from "./public/pages/Features.jsx";
import PricingPage from "./public/pages/Pricing.jsx";
import FaqPage from "./public/pages/Faq.jsx";
import ContactPage from "./public/pages/Contact.jsx";
import PrivacyPage from "./public/pages/Privacy.jsx";
import TermsPage from "./public/pages/Terms.jsx";
import SecurityPage from "./public/pages/Security.jsx";
import CookiesPage from "./public/pages/Cookies.jsx";

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
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/dashboard" replace />;
  return children;
}

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <p className="text-7xl font-black tracking-tight text-brand-200">404</p>
      <h2 className="mt-4 text-xl font-bold text-ink-900">Page Not Found</h2>
      <p className="mt-1 text-sm text-ink-500">
        The page you are looking for does not exist.
      </p>
      <Link
        to="/dashboard"
        className="mt-6 inline-flex items-center gap-2 rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
      >
        Go to Dashboard
      </Link>
    </div>
  );
}

export default function App() {
  const { user } = useAuth();
  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/dashboard" replace /> : <LoginPage />}
      />

      {/* ---- Public marketing pages (no auth) ---- */}
      <Route path="/" element={<PublicLayout><HomePage /></PublicLayout>} />
      <Route path="/about" element={<PublicLayout><AboutPage /></PublicLayout>} />
      <Route path="/why-us" element={<PublicLayout><WhyUsPage /></PublicLayout>} />
      <Route path="/features" element={<PublicLayout><FeaturesPage /></PublicLayout>} />
      <Route path="/pricing" element={<PublicLayout><PricingPage /></PublicLayout>} />
      <Route path="/faq" element={<PublicLayout><FaqPage /></PublicLayout>} />
      <Route path="/contact" element={<PublicLayout><ContactPage /></PublicLayout>} />
      <Route path="/privacy" element={<PublicLayout><PrivacyPage /></PublicLayout>} />
      <Route path="/terms" element={<PublicLayout><TermsPage /></PublicLayout>} />
      <Route path="/security" element={<PublicLayout><SecurityPage /></PublicLayout>} />
      <Route path="/cookies" element={<PublicLayout><CookiesPage /></PublicLayout>} />
      <Route path="/request-demo" element={<PublicLayout><ContactPage /></PublicLayout>} />
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
      <Route
        path="*"
        element={
          <ProtectedRoute>
            <Layout>
              <NotFound />
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}