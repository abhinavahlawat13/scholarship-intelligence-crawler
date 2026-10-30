import os
import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

DB_PATH = os.getenv("DB_PATH", "data/scholarships.db")


class ScholarshipModel(BaseModel):
    # Core Identifiers
    name: str = Field(..., description="Official title of the scholarship")
    source_url: str = Field(..., description="URL where scholarship was found")
    primary_source_url: str = Field(default="Not specified", description="Official portal/domain link")
    organization: str = Field(default="Not specified", description="Offering organization / department")
    category: str = Field(default="Not specified", description="Government, Corporate CSR, Trust, University")

    # Eligibility & Benefits
    target_group: str = Field(default="Not specified", description="Target beneficiaries / demographics")
    academic_criteria: str = Field(default="Not specified", description="Minimum % or CGPA requirement")
    family_income_limit: str = Field(default="Not specified", description="Max annual family income")
    financial_benefit: str = Field(default="Not specified", description="Award amount or stipend")
    documents_required: str = Field(default="Not specified", description="Required paperwork list")

    # Dates & Deadlines
    application_deadline: str = Field(default="Not specified", description="Closing date or Not specified")
    application_mode: str = Field(default="Not specified", description="Online / Offline portal")

    # Verification Engine Fields
    confidence_score: float = Field(default=0.0, ge=0.0, le=100.0)
    verification_status: str = Field(default="REVIEW REQUIRED")  # VERIFIED or REVIEW REQUIRED
    verification_flags: List[str] = Field(default_factory=list)
    raw_evidence_trace: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Key quotes or snippet proving authentic claims"
    )

    # Lifecycle State
    is_stale: bool = Field(default=False)


def init_db(db_path: str = DB_PATH):
    """Initializes the SQLite database tables."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Main scholarships table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scholarships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            source_url TEXT NOT NULL,
            primary_source_url TEXT DEFAULT 'Not specified',
            organization TEXT DEFAULT 'Not specified',
            category TEXT DEFAULT 'Not specified',
            target_group TEXT DEFAULT 'Not specified',
            academic_criteria TEXT DEFAULT 'Not specified',
            family_income_limit TEXT DEFAULT 'Not specified',
            financial_benefit TEXT DEFAULT 'Not specified',
            documents_required TEXT DEFAULT 'Not specified',
            application_deadline TEXT DEFAULT 'Not specified',
            application_mode TEXT DEFAULT 'Not specified',
            confidence_score REAL DEFAULT 0.0,
            verification_status TEXT DEFAULT 'REVIEW REQUIRED',
            verification_flags TEXT,
            raw_evidence_trace TEXT,
            is_stale INTEGER DEFAULT 0,
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Change tracking / audit history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scholarship_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scholarship_name TEXT NOT NULL,
            field_name TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (scholarship_name) REFERENCES scholarships (name)
        )
    """)

    conn.commit()
    conn.close()


def save_or_update_scholarship(data: ScholarshipModel, db_path: str = DB_PATH) -> str:
    """
    Saves new scholarship or detects changes and records an audit log.
    Returns: 'inserted', 'updated', or 'unchanged'
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM scholarships WHERE name = ?", (data.name,))
    existing = cursor.fetchone()

    flags_json = json.dumps(data.verification_flags)
    evidence_json = json.dumps(data.raw_evidence_trace)

    if not existing:
        cursor.execute("""
            INSERT INTO scholarships (
                name, source_url, primary_source_url, organization, category,
                target_group, academic_criteria, family_income_limit, financial_benefit,
                documents_required, application_deadline, application_mode,
                confidence_score, verification_status, verification_flags,
                raw_evidence_trace, is_stale, first_seen_at, last_checked_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (
            data.name, data.source_url, data.primary_source_url, data.organization, data.category,
            data.target_group, data.academic_criteria, data.family_income_limit, data.financial_benefit,
            data.documents_required, data.application_deadline, data.application_mode,
            data.confidence_score, data.verification_status, flags_json,
            evidence_json, 1 if data.is_stale else 0
        ))
        conn.commit()
        conn.close()
        return "inserted"

    # Compare fields for change detection
    fields_to_track = [
        "primary_source_url", "organization", "category", "target_group",
        "academic_criteria", "family_income_limit", "financial_benefit",
        "documents_required", "application_deadline", "application_mode",
        "confidence_score", "verification_status"
    ]

    has_changes = False
    for field in fields_to_track:
        old_val = str(existing[field])
        new_val = str(getattr(data, field))
        if old_val != new_val:
            cursor.execute("""
                INSERT INTO scholarship_history (scholarship_name, field_name, old_value, new_value)
                VALUES (?, ?, ?, ?)
            """, (data.name, field, old_val, new_val))
            has_changes = True

    # Update existing record
    cursor.execute("""
        UPDATE scholarships SET
            source_url = ?, primary_source_url = ?, organization = ?, category = ?,
            target_group = ?, academic_criteria = ?, family_income_limit = ?, financial_benefit = ?,
            documents_required = ?, application_deadline = ?, application_mode = ?,
            confidence_score = ?, verification_status = ?, verification_flags = ?,
            raw_evidence_trace = ?, is_stale = ?, last_checked_at = CURRENT_TIMESTAMP
        WHERE name = ?
    """, (
        data.source_url, data.primary_source_url, data.organization, data.category,
        data.target_group, data.academic_criteria, data.family_income_limit, data.financial_benefit,
        data.documents_required, data.application_deadline, data.application_mode,
        data.confidence_score, data.verification_status, flags_json,
        evidence_json, 1 if data.is_stale else 0, data.name
    ))

    conn.commit()
    conn.close()
    return "updated" if has_changes else "unchanged"