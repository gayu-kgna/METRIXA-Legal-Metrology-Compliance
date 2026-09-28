import { request } from './client';
import { 
  InspectionComplianceSummaryResponse, 
  RuleEvaluationRead 
} from '../types/api';

export interface RuleEvaluationRequestPayload {
  rule_set_version?: string;
  rule_codes?: string[];
  include_test_rules?: boolean;
}

export async function evaluateInspectionRules(
  inspectionId: string,
  payload?: RuleEvaluationRequestPayload
): Promise<InspectionComplianceSummaryResponse> {
  return request<InspectionComplianceSummaryResponse>(
    `/inspections/${inspectionId}/rules/evaluate`,
    {
      method: 'POST',
      body: payload ? JSON.stringify(payload) : undefined,
    }
  );
}

export async function getInspectionRuleEvaluations(
  inspectionId: string,
  evaluationRunId?: string,
  latestOnly: boolean = true
): Promise<RuleEvaluationRead[]> {
  const params = new URLSearchParams();
  if (evaluationRunId) {
    params.set('evaluation_run_id', evaluationRunId);
  } else if (latestOnly) {
    params.set('latest_only', 'true');
  }
  const qs = params.toString() ? `?${params.toString()}` : '';
  return request<RuleEvaluationRead[]>(
    `/inspections/${inspectionId}/rules/evaluations${qs}`
  );
}

export async function getSingleRuleEvaluation(
  inspectionId: string,
  evaluationId: string
): Promise<RuleEvaluationRead> {
  return request<RuleEvaluationRead>(
    `/inspections/${inspectionId}/rules/evaluations/${evaluationId}`
  );
}
