import re
from urllib.parse import urlparse
from datetime import datetime
from typing import Dict, Any, List, Tuple
from src.database import ScholarshipModel

# High authority domain suffixes and primary government/institutional hosts
OFFICIAL_DOMAINS = [
    ".gov.in",
    ".nic.in",
    ".ac.in",
    ".edu.in",
    ".org.in",
    "scholarships.gov.in",
    "ugc.ac.in",
    "aicte-india.org",
    "buddy4study.com"  # Aggregator, needs primary verification
]

# Known corporate foundations / CSR portals
REPUTABLE_CSR_DOMAINS = [
    "tatatrusts.org",
    "reliancefoundation.org",
    "hpe.com",
    "infosys.org",
    "adityabirla.com"
]


def check_domain_authority(url: str) -> Tuple[bool, str]:
    """Evaluates whether the URL belongs to an official or primary institution."""
    if not url or url == "Not specified":
        return False, "No URL provided"

    domain = urlparse(url).netloc.lower()

    for official in OFFICIAL_DOMAINS:
        if official in domain:
            return True, f"Primary domain match: {official}"

    for csr in REPUTABLE_CSR_DOMAINS:
        if csr in domain:
            return True, f"Reputable CSR portal: {csr}"

    return False, f"Third-party or aggregator domain: {domain}"


def parse_and_check_deadline(deadline_str: str) -> Tuple[bool, bool]:
    """
    Checks if a deadline is present, and whether it is already past (stale).
    Returns (has_valid_deadline, is_stale).
    """
    if not deadline_str or deadline_str == "Not specified":
        return False, False

    # Try common date formats (e.g., 2026-11-30, 30-11-2026, 30/11/2026)
    date_patterns = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %B %Y",
        "%B %d, %Y"
    ]

    for pattern in date_patterns:
        try:
            # Clean string for regex-like match
            cleaned = deadline_str.strip()
            parsed_date = datetime.strptime(cleaned, pattern)
            is_stale = parsed_date.date() < datetime.now().date()
            return True, is_stale
        except ValueError:
            continue

    # If date pattern didn't parse strictly, check if explicitly marked closed/expired
    if any(keyword in deadline_str.lower() for keyword in ["closed", "expired", "passed"]):
        return True, True

    return True, False


def calculate_confidence_score(scholarship: ScholarshipModel) -> Tuple[float, str, List[str]]:
    """
    Deterministic scoring rubric:
    - Primary Official Domain Link: +45 pts
    - Official circular / notification present: +20 pts
    - Clean eligibility & benefit criteria (no missing fields): +15 pts
    - Verifiable current deadline: +10 pts
    - Primary contact / direct portal application mode: +10 pts
    Total possible: 100 pts.
    Threshold: >= 95.0 -> VERIFIED, else -> REVIEW REQUIRED
    """
    score = 0.0
    flags = []

    # 1. Primary Source Authority (45 pts)
    is_official, authority_msg = check_domain_authority(scholarship.primary_source_url)
    if is_official:
        score += 45.0
        flags.append(authority_msg)
    else:
        flags.append(f"Authority penalty: {authority_msg}")

    # 2. Raw Evidence Trace / Notification Proof (20 pts)
    if scholarship.raw_evidence_trace and len(scholarship.raw_evidence_trace.keys()) >= 2:
        score += 20.0
        flags.append("Evidence quote verified")
    else:
        flags.append("Sparse or unverified evidence quote")

    # 3. Completeness of Core Criteria (15 pts)
    core_fields = [
        scholarship.academic_criteria,
        scholarship.family_income_limit,
        scholarship.financial_benefit
    ]
    specified_count = sum(1 for field in core_fields if field != "Not specified")
    completeness_pts = (specified_count / len(core_fields)) * 15.0
    score += completeness_pts
    if specified_count == len(core_fields):
        flags.append("Complete eligibility profile")
    else:
        flags.append(f"Incomplete profile: {specified_count}/{len(core_fields)} fields specified")

    # 4. Deadline Verifiability & Freshness (10 pts)
    has_deadline, is_stale = parse_and_check_deadline(scholarship.application_deadline)
    if has_deadline and not is_stale:
        score += 10.0
        flags.append("Valid active deadline confirmed")
    elif is_stale:
        score += 5.0
        flags.append("Deadline is past (stale scheme)")
        scholarship.is_stale = True
    else:
        flags.append("Deadline missing or unverified")

    # 5. Direct Portal / Mode (10 pts)
    if scholarship.application_mode != "Not specified" and "online" in scholarship.application_mode.lower():
        score += 10.0
        flags.append("Direct online application portal verified")
    else:
        flags.append("Unconfirmed application mode")

    # Final Verification Decision
    status = "VERIFIED" if score >= 95.0 else "REVIEW REQUIRED"

    return round(score, 2), status, flags


def evaluate_scholarship(scholarship: ScholarshipModel) -> ScholarshipModel:
    """Applies the verification engine to the scholarship instance."""
    score, status, flags = calculate_confidence_score(scholarship)
    scholarship.confidence_score = score
    scholarship.verification_status = status
    scholarship.verification_flags = flags
    return scholarship