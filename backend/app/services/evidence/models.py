import enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class EvidenceCategory(str, enum.Enum):
    ORIGINAL_IMAGE = "ORIGINAL_IMAGE"
    PROCESSED_IMAGE = "PROCESSED_IMAGE"
    OCR_RUN = "OCR_RUN"
    OCR_REGION = "OCR_REGION"
    ENTITY_PARSE = "ENTITY_PARSE"
    OBSERVATION = "OBSERVATION"
    PDP_GEOMETRY = "PDP_GEOMETRY"
    RULE_DEFINITION = "RULE_DEFINITION"
    RULE_EVALUATION = "RULE_EVALUATION"
    AUDIT_LOG = "AUDIT_LOG"
    INSPECTION_METADATA = "INSPECTION_METADATA"
    ADJUDICATION = "ADJUDICATION"

class EvidenceTraceNode(BaseModel):
    node_id: str
    category: EvidenceCategory
    label: str
    properties: Dict[str, Any] = Field(default_factory=dict)
    parent_ids: List[str] = Field(default_factory=list)

class EvidenceTraceEdge(BaseModel):
    source_id: str
    target_id: str
    relationship: str

class EvidenceTraceGraph(BaseModel):
    nodes: Dict[str, EvidenceTraceNode] = Field(default_factory=dict)
    edges: List[EvidenceTraceEdge] = Field(default_factory=list)

    def add_node(self, node: EvidenceTraceNode):
        self.nodes[node.node_id] = node

    def add_edge(self, source_id: str, target_id: str, relationship: str):
        self.edges.append(EvidenceTraceEdge(source_id=source_id, target_id=target_id, relationship=relationship))

    def trace_lineage(self, start_node_id: str) -> List[EvidenceTraceNode]:
        """Traverse backward from a node to all its evidentiary origins."""
        visited = set()
        lineage = []
        queue = [start_node_id]

        while queue:
            curr_id = queue.pop(0)
            if curr_id in visited:
                continue
            visited.add(curr_id)
            node = self.nodes.get(curr_id)
            if node:
                lineage.append(node)
                for pid in node.parent_ids:
                    if pid not in visited:
                        queue.append(pid)
        return lineage

class IntegrityItem(BaseModel):
    item_id: str
    item_type: str
    sha256_hash: str
    description: Optional[str] = None

class IntegrityManifest(BaseModel):
    algorithm: str = "SHA-256"
    items: List[IntegrityItem] = Field(default_factory=list)

class EvidenceManifest(BaseModel):
    bundle_id: str
    inspection_id: str
    evaluation_run_id: Optional[str] = None
    created_at: str
    application_version: str = "1.0.0"
    parser_version: str = "ENTITY-PARSER-v1"
    normalizer_version: str = "NORMALIZER-v1"
    ocr_provider: str = "Modular OCR Engine"
    inspection: Dict[str, Any] = Field(default_factory=dict)
    product: Optional[Dict[str, Any]] = None
    images: List[Dict[str, Any]] = Field(default_factory=list)
    ocr_runs: List[Dict[str, Any]] = Field(default_factory=list)
    observations: List[Dict[str, Any]] = Field(default_factory=list)
    geometry: List[Dict[str, Any]] = Field(default_factory=list)
    rule_evaluations: List[Dict[str, Any]] = Field(default_factory=list)
    audit_logs: List[Dict[str, Any]] = Field(default_factory=list)
    integrity: IntegrityManifest = Field(default_factory=IntegrityManifest)
