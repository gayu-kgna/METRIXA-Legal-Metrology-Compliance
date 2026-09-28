import React from 'react';
import { NavLink, useParams } from 'react-router-dom';
import { 
  LayoutDashboard, 
  FolderKanban, 
  PlusCircle, 
  Camera, 
  Cpu, 
  Scale, 
  GitBranch, 
  FileText,
  PackageCheck,
  Crosshair,
  Layers,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const { inspectionId } = useParams<{ inspectionId?: string }>();

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      backgroundColor: 'var(--bg-surface-primary)',
      borderRight: '1px solid var(--border-subtle)',
      position: 'fixed',
      top: 'var(--navbar-height)',
      bottom: 0,
      left: 0,
      overflowY: 'auto',
      padding: '20px 12px',
      zIndex: 90,
      display: 'flex',
      flexDirection: 'column',
      gap: 24,
    }}>
      {/* Primary Navigation */}
      <div>
        <div style={{
          fontSize: '0.72rem',
          fontWeight: 600,
          color: 'var(--text-muted)',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          padding: '0 12px 8px',
        }}>
          General
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <NavLink
            to="/dashboard"
            className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
            style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
          >
            <LayoutDashboard size={17} />
            <span>Dashboard</span>
          </NavLink>

          <NavLink
            to="/products"
            className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
            style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            id="nav-product-ledger"
          >
            <Layers size={17} />
            <span>Product Ledger</span>
          </NavLink>

          <NavLink
            to="/inspections"
            end
            className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
            style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
          >
            <FolderKanban size={17} />
            <span>All Inspections</span>
          </NavLink>

          <NavLink
            to="/inspections/new"
            className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
            style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
          >
            <PlusCircle size={17} />
            <span>New Inspection</span>
          </NavLink>
        </nav>
      </div>

      {/* Active Inspection Context Navigation */}
      {inspectionId && (
        <div style={{
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: 16,
        }}>
          <div style={{
            fontSize: '0.72rem',
            fontWeight: 600,
            color: 'var(--accent-cyan)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            padding: '0 12px 8px',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
          }}>
            <PackageCheck size={14} />
            <span>Active Session</span>
          </div>

          <nav style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <NavLink
              to={`/inspections/${inspectionId}`}
              end
              className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            >
              <PackageCheck size={16} />
              <span>Overview</span>
            </NavLink>

            <NavLink
              to={`/inspections/${inspectionId}/capture`}
              className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            >
              <Camera size={16} />
              <span>6-Surface Capture</span>
            </NavLink>

            <NavLink
              to={`/inspections/${inspectionId}/review`}
              className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            >
              <Cpu size={16} />
              <span>Pipeline Stepper</span>
            </NavLink>

            <NavLink
              to={`/inspections/${inspectionId}/results`}
              className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            >
              <Scale size={16} />
              <span>Statutory Results</span>
            </NavLink>

            <NavLink
              to={`/inspections/${inspectionId}/adjudication`}
              className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            >
              <Crosshair size={16} />
              <span>Adjudication</span>
            </NavLink>

            <NavLink
              to={`/inspections/${inspectionId}/evidence`}
              className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            >
              <GitBranch size={16} />
              <span>Evidence Trace</span>
            </NavLink>

            <NavLink
              to={`/inspections/${inspectionId}/reports`}
              className={({ isActive }) => `btn ${isActive ? 'btn-primary' : 'btn-outline'}`}
              style={{ justifyContent: 'flex-start', border: 'none', width: '100%' }}
            >
              <FileText size={16} />
              <span>PDF Dossiers</span>
            </NavLink>
          </nav>
        </div>
      )}
    </aside>
  );
};
