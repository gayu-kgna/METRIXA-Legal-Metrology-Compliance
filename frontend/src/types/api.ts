/**
 * Metrixa Comprehensive Type Definitions
 * Legal Metrology Inspection Platform (Packaged Commodities Rules, 2011)
 */

export interface ResponseEnvelope<T> {
  success: boolean;
  message?: string | null;
  data?: T | null;
  error?: {
    code?: string;
    message?: string;
    details?: any;
  } | null;
}

export type UserRole = 'ADMIN' | 'SENIOR_INSPECTOR' | 'FIELD_OFFICER' | 'VIEWER';

export interface User {
  id: string;
  username: string;
  email: string;
  full_name?: string | null;
  badge_number?: string | null;
  role: UserRole;
  is_active: boolean;
  jurisdiction_code?: string | null;
}

export interface AuthTokens {
  access_token: string;
  token_type: string;
}

export interface Product {
  id: string;
  gtin_barcode?: string | null;
  brand_name: string;
  product_name: string;
  category?: string | null;
  commodity_type?: string | null;
  manufacturer_claimed?: string | null;
  metadata_json?: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

export type InspectionOverallStatus = 'DRAFT' | 'IN_PROGRESS' | 'PENDING_REVIEW' | 'COMPLETED' | 'CANCELLED';

export type SurfaceType = 
  | 'FRONT_PDP'
  | 'BACK'
  | 'LEFT'
  | 'RIGHT'
  | 'TOP'
  | 'BOTTOM'
  | 'UNSPECIFIED';

export interface SurfaceRead {
  id: string;
  inspection_id: string;
  surface_type: SurfaceType;
  image_storage_path: string;
  sha256_hash: string;
  image_width?: number | null;
  image_height?: number | null;
  file_size_bytes?: number | null;
  original_filename?: string | null;
  mime_type?: string | null;
  detected_format?: string | null;
  quality_metrics?: Record<string, any>;
  captured_at: string;
  created_at: string;
}

export interface ImageUploadResponse {
  id: string;
  inspection_id: string;
  surface_type: SurfaceType;
  original_filename?: string | null;
  mime_type: string;
  detected_format: string;
  file_size_bytes: number;
  image_width: number;
  image_height: number;
  sha256_hash: string;
  storage_reference: string;
  is_duplicate: boolean;
  duplicate_of_surface_id?: string | null;
  captured_at: string;
  quality_metrics: Record<string, any>;
}

export interface Inspection {
  id: string;
  inspection_number: string;
  product_id?: string | null;
  product?: Product | null;
  inspector_id: string;
  overall_status: InspectionOverallStatus;
  retail_outlet_name?: string | null;
  retail_outlet_address?: string | null;
  geo_coordinates?: Record<string, any>;
  notes?: string | null;
  initiated_at: string;
  completed_at?: string | null;
  created_at: string;
  updated_at: string;
  surfaces?: SurfaceRead[];
  observations?: ObservationRead[];
  evaluations?: RuleEvaluationRead[];
  evidence_items?: any[];
}

export interface CreateInspectionPayload {
  product_id?: string | null;
  retail_outlet_name: string;
  retail_outlet_address?: string | null;
  geo_coordinates?: {
    latitude?: number;
    longitude?: number;
  };
  notes?: string | null;
}

// OCR Types
export interface OCRBBox {
  x: number;
  y: number;
  width: number;
  height: number;
  xmin?: number;
  ymin?: number;
  xmax?: number;
  ymax?: number;
}

export interface OCRRegion {
  id: string;
  surface_id?: string;
  ocr_run_id?: string;
  run_id?: string;
  text: string;
  raw_text?: string;
  confidence: number;
  bbox?: OCRBBox;
  bounding_box: OCRBBox;
  polygon_coords?: Record<string, any>;
  token_order?: number;
}

export interface OCRRun {
  id: string;
  surface_id: string;
  ocr_provider: string;
  preprocessing_variant: string;
  raw_text: string;
  mean_confidence?: number | null;
  character_count?: number | null;
  execution_duration_ms?: number | null;
  created_at: string;
  regions?: OCRRegion[];
  region_count?: number;
  total_regions?: number;
}

export interface OCRRunResponse {
  id?: string;
  ocr_run_id: string;
  surface: string;
  surface_id?: string;
  inspection_id?: string;
  provider: string;
  provider_name?: string;
  status: 'COMPLETED' | 'EMPTY' | 'FAILED' | 'PROVIDER_UNAVAILABLE' | string;
  region_count: number;
  total_regions: number;
  total_regions_detected?: number;
  duration_ms: number;
  total_duration_ms?: number;
  error_message?: string | null;
  regions: OCRRegion[];
  run?: OCRRun;
}

export interface OCRRunListResponse {
  surface_id: string;
  total_runs: number;
  runs: OCRRunResponse[];
}

// Entity & Observation Types
export interface ObservationRead {
  id: string;
  inspection_id: string;
  surface_id?: string | null;
  ocr_region_id?: string | null;
  field_type: string;
  field_name?: string;
  raw_value: string;
  raw_text_extracted?: string | null;
  normalized_value: Record<string, any>;
  confidence?: number;
  confidence_score?: number;
  uncertainty_margin?: number | null;
  is_verified_by_inspector?: boolean;
  status?: string;
  bounding_box?: Record<string, any>;
  evidence_reference?: string | null;
  revision?: number;
  is_latest?: boolean;
  superseded_by_id?: string | null;
  revision_reason?: string | null;
  observed_at?: string;
  created_at: string;
}

export interface EntityRunResponse {
  id: string;
  surface_id: string;
  ocr_run_id: string;
  entity_count: number;
  status: string;
  duration_ms: number;
  observations: ObservationRead[];
  created_at: string;
}

export interface EntityRunListResponse {
  surface_id: string;
  total_runs: number;
  runs: EntityRunResponse[];
}

// Geometry Types
export interface PDPGeometryResponse {
  id: string;
  inspection_id?: string;
  surface_id: string;
  surface_type?: string;
  is_pdp_candidate?: boolean;
  image_width?: number;
  image_height?: number;
  image_width_px?: number;
  image_height_px?: number;
  pdp_pixel_area?: number;
  pdp_area_px2: number;
  has_calibration?: boolean;
  is_calibrated: boolean;
  scale_px_per_mm?: number | null;
  physical_width_mm?: number | null;
  physical_height_mm?: number | null;
  estimated_physical_width_mm?: number | null;
  estimated_physical_height_mm?: number | null;
  estimated_physical_area_sq_cm?: number | null;
  pdp_area_cm2?: number | null;
  min_mandatory_numeral_height_mm?: number | null;
  min_actual_numeral_height_mm?: number | null;
  calibration_source?: string | null;
  status: string;
  created_at?: string;
  analyzed_at?: string;
}

export interface PDPGeometryListResponse {
  surface_id: string;
  total_analyses: number;
  analyses: PDPGeometryResponse[];
}

// Rule Engine Types
export type RuleOutcome = 
  | 'PASS' 
  | 'FAIL' 
  | 'REVIEW' 
  | 'INDETERMINATE' 
  | 'NOT_APPLICABLE';

export interface RuleDefinitionRead {
  id: string;
  rule_code: string;
  legal_act: string;
  rule_reference: string;
  clause_reference?: string | null;
  title: string;
  description: string;
  severity: string;
  version: string;
}

export interface RuleEvaluationRead {
  id: string;
  inspection_id: string;
  evaluation_run_id: string;
  rule_definition_id: string;
  rule_code: string;
  rule_version: string;
  outcome: RuleOutcome;
  statutory_citation: string;
  legal_rationale: string;
  measured_value?: any;
  threshold_value?: any;
  tolerance_applied?: any;
  measurement_uncertainty?: any;
  evaluated_at: string;
  rule_definition?: RuleDefinitionRead | null;
  evidence_records?: any[];
}

export interface InspectionComplianceSummaryResponse {
  inspection_id: string;
  evaluation_run_id: string;
  evaluated_at: string;
  rule_set_version?: string;
  total_rules?: number;
  total_rules_evaluated?: number;
  overall_verdict: RuleOutcome;
  pass_count: number;
  fail_count: number;
  review_count: number;
  indeterminate_count: number;
  not_applicable_count: number;
  evaluations: RuleEvaluationRead[];
}

// Evidence & Report Types
export interface EvidenceBundleResponse {
  manifest: Record<string, any>;
  integrity_hash: string;
  snapshot_id?: string | null;
  graph?: Record<string, any> | null;
}

export interface EvidenceSnapshotRead {
  id: string;
  inspection_id: string;
  evaluation_run_id?: string | null;
  integrity_hash: string;
  created_by_id: string;
  created_at: string;
  manifest_json: Record<string, any>;
}

export interface ReportRead {
  id: string;
  inspection_id: string;
  evidence_snapshot_id: string;
  report_type?: string;
  report_version: number;
  pdf_filename?: string;
  storage_path: string;
  sha256_hash: string;
  file_size_bytes?: number | null;
  generated_at: string;
  generated_by_id?: string | null;
  metadata_json?: Record<string, any>;
}

// ============================================================================
// Phase 8: Adjudication & Bounding Box Workspace Types
// ============================================================================

export interface BoundingBoxNormalized {
  ymin: number;
  xmin: number;
  ymax: number;
  xmax: number;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
}

export type CorrectionType =
  | 'TEXT_CORRECTION'
  | 'BOUNDING_BOX_CORRECTION'
  | 'REGION_CREATED'
  | 'REGION_REJECTED'
  | 'REGION_SPLIT'
  | 'REGION_MERGED'
  | 'MANUAL_DECLARATION';

export type ObservationStatus =
  | 'OBSERVED'
  | 'VERIFIED'
  | 'CORRECTED'
  | 'UNCERTAIN'
  | 'REJECTED';

export type ObservationSource =
  | 'PIPELINE_EXTRACTION'
  | 'OFFICER_INPUT';

export interface OCRAdjudication {
  id: string;
  inspection_id: string;
  ocr_region_id?: string | null;
  surface_id?: string | null;
  adjudicator_id: string;
  correction_type: CorrectionType;
  original_text?: string | null;
  corrected_text?: string | null;
  original_bounding_box?: Record<string, any> | null;
  corrected_bounding_box?: Record<string, any> | null;
  reason?: string | null;
  revision: number;
  is_active: boolean;
  status: string;
  created_at: string;
}

export interface AdjudicatedOCRRegion {
  id: string;
  surface_id: string;
  ocr_run_id?: string | null;
  raw_text: string;
  original_text?: string;
  effective_text: string;
  confidence: number;
  bounding_box: BoundingBoxNormalized;
  effective_bounding_box: BoundingBoxNormalized;
  original_bounding_box?: BoundingBoxNormalized;
  status?: string;
  correction_type?: string | null;
  is_adjudicated: boolean;
  adjudication_id?: string | null;
  revision?: number;
  reason?: string | null;
  adjudicated_by?: string | null;
  adjudicated_at?: string | null;
  linked_observation_id?: string | null;
  linked_field_type?: string | null;
  is_rejected: boolean;
  is_manually_created: boolean;
  active_adjudication?: OCRAdjudication | null;
}

export interface AdjudicatedObservation {
  id: string;
  inspection_id: string;
  surface_id?: string | null;
  ocr_region_id?: string | null;
  field_type: string;
  raw_value: string;
  normalized_value: Record<string, any>;
  confidence: number;
  status: ObservationStatus;
  source: ObservationSource;
  revision: number;
  is_latest: boolean;
  created_at: string;
  updated_at: string;
  surface_name?: string | null;
  field_display_name?: string | null;
}

export interface ConflictGroup {
  field_type: string;
  observation_count: number;
  observations: AdjudicatedObservation[];
  has_conflict: boolean;
  description: string;
}

export interface AdjudicationWorkspaceState {
  inspection_id: string;
  inspection_number: string;
  total_regions: number;
  adjudicated_regions_count: number;
  rejected_regions_count: number;
  total_observations: number;
  verified_observations_count: number;
  conflict_count: number;
  regions: AdjudicatedOCRRegion[];
  observations: AdjudicatedObservation[];
  conflicts: ConflictGroup[];
  surfaces: SurfaceRead[];
}

export interface RuleEvaluationChange {
  rule_code: string;
  title: string;
  previous_outcome?: string | null;
  new_outcome: string;
  statutory_citation: string;
  changed: boolean;
  legal_rationale: string;
}

export interface RuleReevaluationResponse {
  inspection_id: string;
  evaluation_run_id: string;
  previous_verdict: string;
  new_verdict: string;
  verdict_changed: boolean;
  total_rules: number;
  changes: RuleEvaluationChange[];
  reevaluated_at: string;
  summary: InspectionComplianceSummaryResponse;
}

export interface OCRRegionPatchRequest {
  corrected_text?: string;
  corrected_bounding_box?: BoundingBoxNormalized;
  reason?: string;
}

export interface OCRRegionCreateRequest {
  surface_id: string;
  raw_text: string;
  bounding_box: BoundingBoxNormalized;
  reason?: string;
}

export interface ManualObservationCreateRequest {
  surface_id?: string;
  ocr_region_id?: string;
  field_type: string;
  raw_value: string;
  normalized_value: Record<string, any>;
  reason?: string;
}

export interface ObservationCorrectRequest {
  raw_value?: string;
  normalized_value?: Record<string, any>;
  status?: ObservationStatus;
  reason?: string;
}

// Phase 9: Product Ledger, Historical Timeline & Dashboard Analytics Types

export interface ProductLedgerItem {
  id: string;
  gtin_barcode?: string | null;
  brand_name: string;
  product_name: string;
  category?: string | null;
  commodity_type?: string | null;
  manufacturer_claimed?: string | null;
  inspection_count: number;
  latest_inspection_date?: string | null;
  latest_label_version?: string | null;
  latest_status?: string | null;
  created_at: string;
}

export interface ProductDetail {
  id: string;
  gtin_barcode?: string | null;
  brand_name: string;
  product_name: string;
  category?: string | null;
  commodity_type?: string | null;
  manufacturer_claimed?: string | null;
  metadata_json: Record<string, any>;
  known_declarations: Record<string, any>;
  inspection_count: number;
  first_inspection_date?: string | null;
  latest_inspection_date?: string | null;
  latest_status?: string | null;
  latest_label_version?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LabelVersionDetail {
  id: string;
  product_id: string;
  version_tag: string;
  version_fingerprint?: string | null;
  canonical_declarations: Record<string, any>;
  source_inspection_id?: string | null;
  source_inspection_number?: string | null;
  evidence_snapshot_id?: string | null;
  notes?: string | null;
  effective_from?: string | null;
  effective_to?: string | null;
  created_at: string;
}

export interface FieldComparisonItem {
  field: string;
  field_label: string;
  prev_value?: any;
  curr_value?: any;
  prev_source?: string | null;
  curr_source?: string | null;
}

export interface LabelDiffResponse {
  from_version_id: string;
  from_version_tag: string;
  to_version_id: string;
  to_version_tag: string;
  changed_fields: FieldComparisonItem[];
  added_fields: FieldComparisonItem[];
  removed_fields: FieldComparisonItem[];
  unchanged_fields: FieldComparisonItem[];
  total_changes: number;
  legal_disclaimer: string;
}

export interface TimelineEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  title: string;
  description: string;
  actor_name?: string | null;
  actor_role?: string | null;
  badge_number?: string | null;
  inspection_id?: string | null;
  inspection_number?: string | null;
  metadata: Record<string, any>;
}

export interface ProductInspectionItem {
  id: string;
  inspection_number: string;
  initiated_at: string;
  completed_at?: string | null;
  retail_outlet_name?: string | null;
  retail_outlet_address?: string | null;
  inspector_name?: string | null;
  inspector_badge?: string | null;
  overall_status: string;
  label_version_tag?: string | null;
  rule_verdict?: string | null;
  has_report: boolean;
  report_id?: string | null;
  report_pdf_path?: string | null;
}

export interface AnalyticsOverview {
  total_inspections: number;
  inspections_this_month: number;
  inspections_this_week: number;
  products_inspected: number;
  reports_generated: number;
  inspections_requiring_review: number;
  rule_evaluation_outcomes: Record<string, number>;
  total_adjudications: number;
  adjudications_by_type: Record<string, number>;
}

export interface TrendDataPoint {
  date: string;
  count: number;
}

export interface OutcomeDistribution {
  pass_count: number;
  review_count: number;
  fail_count: number;
  uncertain_count: number;
  total_evaluations: number;
}

export interface CategoryDistributionItem {
  category: string;
  count: number;
  percentage: number;
}

export interface LocationDistributionItem {
  location: string;
  count: number;
  pass_count: number;
  fail_count: number;
  review_count: number;
}

export interface AdjudicationActivityItem {
  date: string;
  correction_type: string;
  count: number;
}

