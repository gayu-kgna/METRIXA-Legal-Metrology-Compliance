import time
import uuid
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.inspection import Inspection
from app.models.surface import InspectionSurface
from app.models.ocr_run import OCRRun
from app.models.ocr_region import OCRRegion
from app.models.observation import Observation
from app.models.entity_run import EntityParsingRun
from app.models.enums import ObservationSource, ObservationStatus, FieldType
from app.services.entity.models import ParsedEntity, PARSER_VERSION, NORMALIZER_VERSION
from app.services.entity.classifiers import EntityClassifier
from app.services.entity.normalizer import EntityNormalizer

logger = logging.getLogger("metrixa.entity.parser")

class EntityParsingService:
    """
    Dedicated domain service orchestrating the semantic entity parsing and normalization pipeline.
    Transforms raw OCR perceptual evidence (OCRRegion) into structured statutory declarations (Observation)
    while preserving complete provenance, distinguishing raw from normalized values, and detecting conflicts.
    """

    def __init__(
        self,
        classifier: Optional[EntityClassifier] = None,
        normalizer: Optional[EntityNormalizer] = None,
    ):
        self.normalizer = normalizer or EntityNormalizer()
        self.classifier = classifier or EntityClassifier(normalizer=self.normalizer)

    def detect_conflicts(self, entities: List[ParsedEntity]) -> None:
        """
        Identify conflicting statutory declarations on the same package (e.g. multiple distinct MRPs or Net Quantities).
        Marks conflicting entities with ObservationStatus.CONFLICTING without silently choosing one.
        """
        # Group by field type
        field_groups: Dict[FieldType, List[ParsedEntity]] = {}
        for ent in entities:
            field_groups.setdefault(ent.field_type, []).append(ent)

        for ftype, items in field_groups.items():
            if len(items) > 1:
                # Check if values diverge significantly
                unique_vals = {str(item.normalized_value.get("value", item.raw_value)) for item in items}
                if len(unique_vals) > 1:
                    logger.warning("Conflicting declarations detected for %s: %s", ftype.value, unique_vals)
                    for item in items:
                        item.status = ObservationStatus.CONFLICTING
                        item.is_conflicting = True
                        item.conflict_details = {
                            "divergent_values": list(unique_vals),
                            "competing_raw_snippets": [i.raw_value for i in items],
                        }

    async def execute_entity_pipeline(
        self,
        db: AsyncSession,
        inspection: Inspection,
        surface: InspectionSurface,
        ocr_run_id: Optional[uuid.UUID] = None,
    ) -> EntityParsingRun:
        """
        Execute entity parsing pipeline on package surface OCR evidence:
        1. Resolves OCRRun and OCRRegion tokens.
        2. Executes deterministic statutory entity classification.
        3. Normalizes all quantities, prices, dates, parties, and contact info.
        4. Detects conflicts and flags ambiguities.
        5. Persists an immutable EntityParsingRun record.
        6. Persists structured Observation entities linked to source OCR regions.
        """
        start_time = time.perf_counter()

        # 1. Resolve OCRRun
        if ocr_run_id:
            query = select(OCRRun).options(selectinload(OCRRun.regions)).where(OCRRun.id == ocr_run_id)
            res = await db.execute(query)
            ocr_run = res.scalar_one_or_none()
            if not ocr_run:
                raise FileNotFoundError(f"Specified OCR run '{ocr_run_id}' not found.")
            if ocr_run.status != "COMPLETED":
                raise ValueError(
                    f"Specified OCR run '{ocr_run_id}' has status '{ocr_run.status}'. "
                    "Entity parsing requires a COMPLETED OCR run."
                )
        else:
            # Pick latest completed OCR run for this surface
            query = (
                select(OCRRun)
                .options(selectinload(OCRRun.regions))
                .where(OCRRun.surface_id == surface.id, OCRRun.status == "COMPLETED")
                .order_by(OCRRun.executed_at.desc())
            )
            res = await db.execute(query)
            ocr_run = res.scalars().first()
            if not ocr_run:
                raise ValueError(
                    f"No completed OCR run found for surface '{surface.id}'. "
                    "Run OCR first before executing entity parsing."
                )

        regions: List[OCRRegion] = ocr_run.regions or []
        raw_full_text = ocr_run.metadata_json.get("raw_text", "")

        # 2. Classify and parse entities
        parsed_entities = self.classifier.classify_and_parse(regions, raw_full_text)

        # 3. Detect conflicts
        self.detect_conflicts(parsed_entities)

        # Count metrics
        conflicts_count = sum(1 for e in parsed_entities if e.is_conflicting)
        ambiguities_count = sum(1 for e in parsed_entities if e.is_ambiguous)
        total_duration_ms = (time.perf_counter() - start_time) * 1000.0

        run_status = "COMPLETED"
        if not parsed_entities:
            run_status = "EMPTY"
        elif conflicts_count > 0:
            run_status = "CONFLICTS_DETECTED"

        # 4. Create EntityParsingRun record
        entity_run = EntityParsingRun(
            id=uuid.uuid4(),
            inspection_id=inspection.id,
            surface_id=surface.id,
            ocr_run_id=ocr_run.id,
            parser_version=PARSER_VERSION,
            normalizer_version=NORMALIZER_VERSION,
            total_entities_extracted=len(parsed_entities),
            total_conflicts_detected=conflicts_count,
            total_ambiguities_detected=ambiguities_count,
            status=run_status,
            duration_ms=round(total_duration_ms, 2),
            metadata_json={
                "ocr_provider": ocr_run.provider_name,
                "preprocessing_variant": ocr_run.preprocessing_variant,
                "total_ocr_regions_scanned": len(regions),
            },
        )
        db.add(entity_run)

        # 5. Handle revision history for prior observations on this surface
        prev_obs_query = select(Observation).where(
            Observation.inspection_id == inspection.id,
            Observation.surface_id == surface.id,
            Observation.is_latest == True,
        )
        prev_obs_res = await db.execute(prev_obs_query)
        prior_active_observations = prev_obs_res.scalars().all()
        # Group prior observations by field_type
        prev_obs_by_type: Dict[FieldType, List[Observation]] = {}
        for p_obs in prior_active_observations:
            prev_obs_by_type.setdefault(p_obs.field_type, []).append(p_obs)

        # 6. Phase 1: Instantiate and add all new Observation records
        new_observations: List[Observation] = []
        supersession_pairs: List[tuple[Observation, Observation]] = []

        for ent in parsed_entities:
            primary_region_id = ent.source_region_ids[0] if ent.source_region_ids else None
            norm_payload = {
                **ent.normalized_value,
                "source_ocr_region_ids": [str(rid) for rid in ent.source_region_ids],
                "source_ocr_run_id": str(ocr_run.id),
                "parser_version": PARSER_VERSION,
                "normalizer_version": NORMALIZER_VERSION,
            }
            if ent.is_ambiguous:
                norm_payload["ambiguity_reason"] = ent.ambiguity_reason
            if ent.is_conflicting:
                norm_payload["conflict_details"] = ent.conflict_details

            obs_id = uuid.uuid4()
            rev = 1
            # Check if this field_type had prior active observation(s)
            p_list = prev_obs_by_type.get(ent.field_type, [])
            if p_list:
                # Use the highest revision among prior active observations
                max_rev = max(p.revision for p in p_list)
                rev = max_rev + 1

            obs = Observation(
                id=obs_id,
                inspection_id=inspection.id,
                surface_id=surface.id,
                ocr_region_id=primary_region_id,
                entity_run_id=entity_run.id,
                field_type=ent.field_type,
                raw_value=ent.raw_value,
                normalized_value=norm_payload,
                source=ObservationSource.SYSTEM,
                confidence=round(ent.confidence, 4),
                status=ent.status,
                bounding_box=ent.bounding_box,
                revision=rev,
                is_latest=True,
            )
            db.add(obs)
            new_observations.append(obs)

            # Record supersession pair(s)
            for p_obs in p_list:
                supersession_pairs.append((p_obs, obs))
            # Remove from dict so subsequent entities of same field_type don't duplicate supersession
            if ent.field_type in prev_obs_by_type:
                del prev_obs_by_type[ent.field_type]

        try:
            # STEP A: Flush all newly added observations FIRST so their UUIDs physically exist in PostgreSQL
            await db.flush()

            # STEP B: Now update prior observations with valid superseded_by_id foreign keys
            for prior_obs, superseding_obs in supersession_pairs:
                prior_obs.is_latest = False
                prior_obs.superseded_by_id = superseding_obs.id
                prior_obs.revision_reason = f"Re-parsed in entity parsing run {entity_run.id}"

            # STEP C: Commit the full transaction atomically
            await db.commit()
            await db.refresh(entity_run)
        except Exception as e:
            await db.rollback()
            try:
                failed_run = EntityParsingRun(
                    id=uuid.uuid4(),
                    inspection_id=inspection.id,
                    surface_id=surface.id,
                    ocr_run_id=ocr_run.id,
                    parser_version=PARSER_VERSION,
                    normalizer_version=NORMALIZER_VERSION,
                    total_entities_extracted=0,
                    total_conflicts_detected=0,
                    total_ambiguities_detected=0,
                    status="FAILED",
                    duration_ms=round(total_duration_ms, 2),
                    error_message=str(e),
                    metadata_json={"error": str(e)},
                )
                db.add(failed_run)
                await db.commit()
            except Exception:
                await db.rollback()
            logger.error("Entity parsing transaction failed: %s", str(e), exc_info=True)
            raise

        logger.info(
            "Entity pipeline finished: run_id=%s, entities=%d, conflicts=%d, duration=%.2fms",
            entity_run.id, len(parsed_entities), conflicts_count, total_duration_ms
        )
        return entity_run

    async def get_entity_runs_for_surface(
        self,
        db: AsyncSession,
        surface_id: uuid.UUID,
    ) -> List[EntityParsingRun]:
        """Retrieve historical entity parsing runs for a package surface."""
        query = (
            select(EntityParsingRun)
            .options(selectinload(EntityParsingRun.observations))
            .where(EntityParsingRun.surface_id == surface_id)
            .order_by(EntityParsingRun.executed_at.desc())
        )
        res = await db.execute(query)
        return list(res.scalars().all())
