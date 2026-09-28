import React from 'react';
import { 
  Camera, 
  Eye, 
  FileText, 
  Ruler, 
  Scale, 
  CheckCircle2, 
  Clock, 
  AlertCircle 
} from 'lucide-react';

export type PipelineStage = 
  | 'INGESTION' 
  | 'OCR' 
  | 'ENTITIES' 
  | 'GEOMETRY' 
  | 'RULES' 
  | 'DOSSIER';

interface StepDef {
  key: PipelineStage;
  label: string;
  icon: React.ReactNode;
}

const STEPS: StepDef[] = [
  { key: 'INGESTION', label: '1. Ingestion', icon: <Camera size={16} /> },
  { key: 'OCR', label: '2. OCR Perception', icon: <Eye size={16} /> },
  { key: 'ENTITIES', label: '3. Declarations', icon: <FileText size={16} /> },
  { key: 'GEOMETRY', label: '4. PDP Geometry', icon: <Ruler size={16} /> },
  { key: 'RULES', label: '5. Legal Rules', icon: <Scale size={16} /> },
  { key: 'DOSSIER', label: '6. PDF Dossier', icon: <CheckCircle2 size={16} /> },
];

interface PipelineStepperProps {
  currentStage: PipelineStage;
  stageStatuses?: Partial<Record<PipelineStage, 'idle' | 'running' | 'completed' | 'failed'>>;
  onSelectStage?: (stage: PipelineStage) => void;
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  currentStage,
  stageStatuses = {},
  onSelectStage,
}) => {
  const currentIndex = STEPS.findIndex((s) => s.key === currentStage);

  return (
    <div className="stepper-container">
      {STEPS.map((step, idx) => {
        const isCurrent = step.key === currentStage;
        const status = stageStatuses[step.key] || (idx < currentIndex ? 'completed' : 'idle');
        const isCompleted = status === 'completed';
        const isRunning = status === 'running';
        const isFailed = status === 'failed';

        return (
          <div
            key={step.key}
            className="step-item"
            style={{ cursor: onSelectStage ? 'pointer' : 'default' }}
            onClick={() => onSelectStage && onSelectStage(step.key)}
          >
            <div
              className={`step-circle ${
                isCompleted ? 'completed' : isCurrent || isRunning ? 'active' : ''
              } ${isRunning ? 'pulsing' : ''}`}
              style={{
                backgroundColor: isFailed ? 'var(--verdict-fail)' : undefined,
                borderColor: isFailed ? 'var(--verdict-fail)' : undefined,
              }}
            >
              {isRunning ? (
                <Clock size={16} className="animate-spin" />
              ) : isFailed ? (
                <AlertCircle size={16} />
              ) : (
                step.icon
              )}
            </div>
            <div className={`step-label ${isCurrent ? 'active' : ''}`}>
              {step.label}
            </div>
          </div>
        );
      })}
    </div>
  );
};
