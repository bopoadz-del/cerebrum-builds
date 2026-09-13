"""patient_records_management — REUSE knowledge + vector_search + memory."""

from __future__ import annotations

from typing import Any, Dict

from app.block_inputs import knowledge_input, memory_input, vector_search_input
from app.dispatch import BLOCK_DEFAULT_ACTIONS, execute
from app.domain import (
    allowed_next_status,
    chart_class,
    envelope_status,
    knowledge_source_class,
    patient_risk_band,
)
from app.persist import ok_envelope

# READS: caller.input, env.process, config.runtime, database.vector, memory.cache
# WRITES: caller.output, memory.cache
# NEVER: (none)

BLOCK_IDS = ["knowledge", "vector_search", "memory"]
CAPABILITY_ID = "patient_records_management"
SPECIES = ("canine", "feline", "exotic", "equine")


def handle(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Chart a patient: classify species risk, search notes, and cache the record."""
    status = envelope_status(payload)
    species = str(payload.get("species") or "canine")
    if species not in SPECIES:
        species = "canine"
    patient_name = str(payload.get("patient_name") or payload.get("reference") or "sample")
    risk = patient_risk_band(species)
    source_class = knowledge_source_class(patient_name, species)
    klass = chart_class(species)
    record = {
        **payload,
        "status": status,
        "patient_name": patient_name,
        "species": species,
        "risk_band": risk,
        "chart_class": klass,
        "source_class": source_class,
        "capability": CAPABILITY_ID,
        "channel": "mcp",
    }
    blocks = {
        "knowledge": execute(
            "knowledge",
            knowledge_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("knowledge"),
        ),
        "vector_search": execute(
            "vector_search",
            vector_search_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("vector_search"),
        ),
        "memory": execute(
            "memory",
            memory_input(record),
            action=BLOCK_DEFAULT_ACTIONS.get("memory"),
        ),
    }
    record["chart"] = {
        "patient_name": patient_name,
        "species": species,
        "risk_band": risk,
        "chart_class": klass,
        "source_class": source_class,
        "retrieval": "lexical_plus_vector_search",
        "cached_key": f"vetcare:{record.get('reference') or 'sample'}",
        "allowed_next_status": list(allowed_next_status(status)),
        "searched": True,
    }
    return ok_envelope(CAPABILITY_ID, record, blocks)
