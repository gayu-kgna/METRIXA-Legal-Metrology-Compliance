import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { Navbar } from './components/layout/Navbar';
import { Sidebar } from './components/layout/Sidebar';
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { InspectionListPage } from './pages/InspectionListPage';
import { InspectionCreatePage } from './pages/InspectionCreatePage';
import { InspectionDetailPage } from './pages/InspectionDetailPage';
import { CaptureWorkspacePage } from './pages/CaptureWorkspacePage';
import { ReviewPipelinePage } from './pages/ReviewPipelinePage';
import { ResultsPage } from './pages/ResultsPage';
import { EvidenceBrowserPage } from './pages/EvidenceBrowserPage';
import { ReportsPage } from './pages/ReportsPage';
import { AdjudicationPage } from './pages/AdjudicationPage';
import { ProductLedgerPage } from './pages/ProductLedgerPage';
import { ProductDetailPage } from './pages/ProductDetailPage';

const AppLayout: React.FC = () => {
  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <Navbar />
        <main style={{ flex: 1 }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Route */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Application Routes */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/products" element={<ProductLedgerPage />} />
            <Route path="/products/:productId" element={<ProductDetailPage />} />
            <Route path="/inspections" element={<InspectionListPage />} />
            <Route path="/inspections/new" element={<InspectionCreatePage />} />
            <Route path="/inspections/:inspectionId" element={<InspectionDetailPage />} />
            <Route path="/inspections/:inspectionId/capture" element={<CaptureWorkspacePage />} />
            <Route path="/inspections/:inspectionId/review" element={<ReviewPipelinePage />} />
            <Route path="/inspections/:inspectionId/results" element={<ResultsPage />} />
            <Route path="/inspections/:inspectionId/adjudication" element={<AdjudicationPage />} />
            <Route path="/inspections/:inspectionId/evidence" element={<EvidenceBrowserPage />} />
            <Route path="/inspections/:inspectionId/reports" element={<ReportsPage />} />
          </Route>

          {/* Root Redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
