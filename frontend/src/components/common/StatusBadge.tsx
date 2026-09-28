import React from 'react';
import { 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  HelpCircle, 
  MinusCircle, 
  Clock, 
  CheckCheck, 
  FileEdit 
} from 'lucide-react';
import { RuleOutcome, InspectionOverallStatus } from '../../types/api';

interface StatusBadgeProps {
  status: RuleOutcome | InspectionOverallStatus | string;
  size?: 'sm' | 'md' | 'lg';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, size = 'md' }) => {
  const normStatus = (status || '').toUpperCase();

  switch (normStatus) {
    case 'PASS':
    case 'COMPLIANT':
      return (
        <span className="badge badge-pass" role="status" aria-label="Compliant / Pass">
          <CheckCircle2 size={13} />
          <span>{normStatus === 'COMPLIANT' ? 'COMPLIANT' : 'PASS'}</span>
        </span>
      );

    case 'FAIL':
    case 'NON_COMPLIANT':
      return (
        <span className="badge badge-fail" role="status" aria-label="Non-Compliant / Violation">
          <XCircle size={13} />
          <span>{normStatus === 'NON_COMPLIANT' ? 'NON-COMPLIANT' : 'FAIL'}</span>
        </span>
      );

    case 'REVIEW':
    case 'PENDING_REVIEW':
    case 'IN_REVIEW':
    case 'REVIEW_REQUIRED':
      return (
        <span className="badge badge-review" role="status" aria-label="Requires Inspector Review">
          <AlertTriangle size={13} />
          <span>{normStatus === 'REVIEW_REQUIRED' ? 'REVIEW REQUIRED' : normStatus === 'IN_REVIEW' ? 'IN REVIEW' : normStatus === 'PENDING_REVIEW' ? 'PENDING REVIEW' : 'REVIEW'}</span>
        </span>
      );

    case 'INDETERMINATE':
      return (
        <span className="badge badge-indeterminate" role="status" aria-label="Indeterminate Evidence">
          <HelpCircle size={13} />
          <span>INDETERMINATE</span>
        </span>
      );

    case 'NOT_APPLICABLE':
      return (
        <span className="badge badge-na" role="status" aria-label="Statutory Rule Not Applicable">
          <MinusCircle size={13} />
          <span>NOT APPLICABLE</span>
        </span>
      );

    case 'COMPLETED':
      return (
        <span className="badge badge-pass" role="status">
          <CheckCheck size={13} />
          <span>COMPLETED</span>
        </span>
      );

    case 'IN_PROGRESS':
      return (
        <span className="badge" style={{ backgroundColor: 'rgba(99, 102, 241, 0.15)', color: 'var(--accent-cyan)', borderColor: 'var(--primary-500)' }} role="status">
          <Clock size={13} />
          <span>IN PROGRESS</span>
        </span>
      );

    case 'DRAFT':
      return (
        <span className="badge badge-na" role="status">
          <FileEdit size={13} />
          <span>DRAFT</span>
        </span>
      );

    default:
      return (
        <span className="badge badge-na" role="status">
          <span>{status}</span>
        </span>
      );
  }
};
