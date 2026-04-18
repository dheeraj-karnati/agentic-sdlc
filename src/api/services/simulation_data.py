"""Smart simulation data for D8X demo scenarios.

Detects which demo scenario is being run from uploaded filenames
and returns rich, domain-specific output for each agent.
"""

from __future__ import annotations


def detect_scenario(filenames: list[str]) -> str:
    """Detect demo scenario from uploaded filenames."""
    names_lower = " ".join(f.lower() for f in filenames)
    if any(kw in names_lower for kw in ("health", "hipaa", "patient", "clinical", "healthtrack")):
        return "healthtrack"
    if any(kw in names_lower for kw in ("finpay", "payment", "merchant", "pci", "kyc")):
        return "finpay"
    return "generic"


def classify_file(filename: str) -> dict:
    """Classify a file by name into type, subcategory, and estimated word count."""
    name = filename.lower()
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in ("py", "js", "ts", "java", "cs", "go", "rb", "rs"):
        wc = 1500
        if "legacy" in name or "module" in name:
            return {"file_type": "source_code", "subcategory": "legacy_code", "word_count": wc, "description": f"Legacy source code: classes, functions, potential security issues"}
        return {"file_type": "source_code", "subcategory": "source_code", "word_count": wc, "description": "Source code file"}

    if ext == "sql" or "schema" in name:
        return {"file_type": "database_schema", "subcategory": "database", "word_count": 1200, "description": "Database schema with tables, columns, constraints, and stored procedures"}

    if any(kw in name for kw in ("brd", "requirement", "prd", "functional")):
        return {"file_type": "document", "subcategory": "business_requirements", "word_count": 5500, "description": "Business requirements document with functional and non-functional requirements"}

    if any(kw in name for kw in ("technical", "spec", "architecture", "tech")):
        return {"file_type": "document", "subcategory": "technical_specification", "word_count": 3500, "description": "Technical specification covering architecture, security, and infrastructure"}

    if any(kw in name for kw in ("meeting", "notes", "kickoff", "minutes")):
        return {"file_type": "document", "subcategory": "meeting_notes", "word_count": 2500, "description": "Meeting notes with stakeholder decisions, action items, and open questions"}

    if any(kw in name for kw in ("hipaa", "compliance", "security", "audit")):
        return {"file_type": "document", "subcategory": "compliance_document", "word_count": 2000, "description": "Compliance checklist with gap analysis and remediation requirements"}

    if any(kw in name for kw in ("billing", "workflow", "process", "current")):
        return {"file_type": "document", "subcategory": "process_documentation", "word_count": 1800, "description": "Process documentation with current workflows and pain points"}

    if any(kw in name for kw in ("migration", "data", "analysis")):
        return {"file_type": "document", "subcategory": "migration_analysis", "word_count": 2200, "description": "Data migration analysis with quality issues and conversion strategy"}

    if any(kw in name for kw in ("user", "stories", "epic")):
        return {"file_type": "document", "subcategory": "user_stories", "word_count": 1500, "description": "User stories with acceptance criteria"}

    if any(kw in name for kw in ("api", "endpoint", "swagger")):
        return {"file_type": "document", "subcategory": "api_documentation", "word_count": 2000, "description": "API design documentation with endpoints and schemas"}

    # Default based on extension
    if ext in ("pdf", "docx", "doc", "md", "txt", "html"):
        return {"file_type": "document", "subcategory": "general_document", "word_count": 2000, "description": "Document"}
    if ext in ("xlsx", "csv"):
        return {"file_type": "spreadsheet", "subcategory": "data", "word_count": 500, "description": "Spreadsheet data"}
    if ext in ("png", "jpg", "jpeg", "svg"):
        return {"file_type": "image", "subcategory": "diagram", "word_count": 200, "description": "Image/diagram"}

    return {"file_type": "document", "subcategory": "unknown", "word_count": 1000, "description": "Uploaded file"}


def compute_quality_score(files: list[dict]) -> dict:
    """Compute quality score based on file diversity and content."""
    subcats = {f.get("subcategory") for f in files}
    total_words = sum(f.get("word_count", 0) for f in files)
    has_code = any(f.get("file_type") == "source_code" for f in files)
    has_schema = any(f.get("subcategory") == "database" for f in files)

    score = 50
    if any(s in subcats for s in ("business_requirements",)):
        score += 15
    if any(s in subcats for s in ("technical_specification",)):
        score += 10
    if has_code:
        score += 10
    if has_schema:
        score += 8
    if any(s in subcats for s in ("meeting_notes",)):
        score += 7
    if any(s in subcats for s in ("compliance_document",)):
        score += 5
    if any(s in subcats for s in ("process_documentation", "migration_analysis")):
        score += 5
    if len(subcats) >= 3:
        score += 5
    if len(files) >= 5:
        score += 5
    score = min(score, 100)

    completeness = min(len(subcats) * 15, 100)
    diversity = min(len(subcats) * 20, 100)
    volume = min(total_words // 200, 100)

    warnings = []
    if len(files) < 3:
        warnings.append("Only a few files uploaded. More sources improve analysis accuracy.")
    if not has_code and not has_schema:
        warnings.append("No source code or database schema detected. Adding these improves legacy analysis.")

    return {
        "score": score,
        "completeness": completeness,
        "diversity": diversity,
        "volume": volume,
        "warnings": warnings,
    }


# ═══════════════════════════════════════════════
# HEALTHTRACK SCENARIO DATA
# ═══════════════════════════════════════════════

HEALTHTRACK_RULES = [
    {"id": "BR-001", "name": "Patient registration demographics", "description": "New patient registration requires: legal name, preferred name, DOB, biological sex, gender identity, race, ethnicity, preferred language, marital status, and religion", "source": "HealthTrack-Pro-BRD.md (FR-101)", "confidence": "high", "category": "patient_registration"},
    {"id": "BR-002", "name": "Real-time insurance eligibility", "description": "Insurance eligibility must be verified in real-time via EDI 270/271 with minimum 7 major payers: Medicare, Medicaid NC/VA, BCBS NC, Aetna, Cigna, UnitedHealthcare, Humana", "source": "HealthTrack-Pro-BRD.md (FR-106)", "confidence": "high", "category": "patient_registration"},
    {"id": "BR-003", "name": "Probabilistic duplicate detection", "description": "Duplicate patients detected using weighted algorithm: last name 25%, first name 20%, DOB 25%, SSN last 4 15%, phone 10%, address 5%. Score >= 75% triggers review, >= 90% blocks entry", "source": "HealthTrack-Pro-BRD.md (FR-109)", "confidence": "high", "category": "patient_registration"},
    {"id": "BR-004", "name": "Patient consent management", "description": "Track 5 independent consent types with version history: treatment, HIPAA notice, data sharing, telehealth, research participation. Support re-consent workflows when versions change.", "source": "HealthTrack-Pro-BRD.md (FR-117)", "confidence": "high", "category": "patient_registration"},
    {"id": "BR-005", "name": "Special needs flagging", "description": "Flag patients requiring: interpreter (with language), mobility assistance, behavioral alerts, legal guardian for consent", "source": "HealthTrack-Pro-BRD.md (FR-120)", "confidence": "high", "category": "patient_registration"},
    {"id": "BR-006", "name": "Double-booking prevention", "description": "Appointments must cross-reference 8 sources: physician schedule, room availability, equipment, surgical blocks, on-call rotations, PTO, lunch blocks, and hospital rounding schedules", "source": "HealthTrack-Pro-BRD.md (FR-202)", "confidence": "high", "category": "scheduling"},
    {"id": "BR-007", "name": "Automated appointment reminders", "description": "Send SMS at 48hr and 2hr, email at 72hr, voice call at 24hr before appointment. Configurable per clinic and per patient preference.", "source": "HealthTrack-Pro-BRD.md (FR-205)", "confidence": "high", "category": "scheduling"},
    {"id": "BR-008", "name": "Patient self-scheduling rules", "description": "Self-scheduling limited to: follow-up and telehealth only, previously seen physician only, designated slots only, 24hr minimum advance booking, 24hr cancellation policy", "source": "HealthTrack-Pro-BRD.md (FR-206)", "confidence": "high", "category": "scheduling"},
    {"id": "BR-009", "name": "Waitlist with auto-notification", "description": "When slot opens, auto-notify next patient via SMS+email. Patient has 2-hour confirmation window before next person is notified.", "source": "HealthTrack-Pro-BRD.md (FR-207)", "confidence": "high", "category": "scheduling"},
    {"id": "BR-010", "name": "No-show escalation policy", "description": "Warning letter after 2 no-shows, require deposit after 3, dismissal review after 5 within 12 months", "source": "HealthTrack-Pro-BRD.md (FR-211)", "confidence": "high", "category": "scheduling"},
    {"id": "BR-011", "name": "Walk-in queue management", "description": "Walk-in patients added to queue with chief complaint. Estimated wait time calculated from average visit duration by type + current queue depth.", "source": "HealthTrack-Pro-BRD.md (FR-209)", "confidence": "high", "category": "scheduling"},
    {"id": "BR-012", "name": "Four check-in methods", "description": "Support check-in via: front desk manual, kiosk iPad, mobile QR code scan, or automatic geofencing detection", "source": "HealthTrack-Pro-BRD.md (FR-212)", "confidence": "high", "category": "scheduling"},
    {"id": "BR-013", "name": "Nine clinical note templates", "description": "Support SOAP Note, H&P, Procedure Note, Consultation Note, Discharge Summary, Progress Note, Telephone Encounter, Nursing Assessment, Pre-operative Assessment", "source": "HealthTrack-Pro-BRD.md (FR-301)", "confidence": "high", "category": "clinical"},
    {"id": "BR-014", "name": "Drug interaction checking — 5 types", "description": "Real-time checking: drug-drug, drug-allergy, drug-condition, drug-food, therapeutic duplication, and dose range checking via First Databank", "source": "HealthTrack-Pro-BRD.md (FR-305)", "confidence": "high", "category": "clinical"},
    {"id": "BR-015", "name": "Controlled substance PDMP check", "description": "PDMP query required before prescribing Schedule II-V. Calculate MME and alert at > 90 MME/day. Require informed consent for chronic opioid therapy.", "source": "HealthTrack-Pro-BRD.md (FR-312)", "confidence": "high", "category": "clinical"},
    {"id": "BR-016", "name": "Clinical note co-signing workflow", "description": "Resident creates note → attending reviews → co-signs with attestation → note locked. Addenda allowed after signing without modifying original.", "source": "HealthTrack-Pro-BRD.md (FR-313)", "confidence": "high", "category": "clinical"},
    {"id": "BR-017", "name": "Critical lab result escalation", "description": "Panic values: page ordering physician immediately. If not acknowledged in 15 min, escalate to covering physician. If not acknowledged in 30 min, escalate to department chief.", "source": "HealthTrack-Pro-BRD.md (FR-406)", "confidence": "high", "category": "lab_integration"},
    {"id": "BR-018", "name": "After-visit summary generation", "description": "Auto-generate patient-friendly AVS: diagnoses, medication changes, follow-up instructions, orders, referrals, education materials. Available in English and Spanish minimum.", "source": "HealthTrack-Pro-BRD.md (FR-320)", "confidence": "high", "category": "clinical"},
    {"id": "BR-019", "name": "NLP-based CPT code suggestion", "description": "Analyze clinical note assessment/plan text to recommend appropriate E&M level (99202-99215) based on 2021 MDM-based guidelines", "source": "HealthTrack-Pro-BRD.md (FR-501)", "confidence": "high", "category": "billing"},
    {"id": "BR-020", "name": "Real-time claim scrubbing — 6 checks", "description": "Before submission verify: ICD-CPT compatibility, medical necessity (LCD/NCD), modifier requirements, place of service, authorization on file, timely filing deadline", "source": "HealthTrack-Pro-BRD.md (FR-502)", "confidence": "high", "category": "billing"},
    {"id": "BR-021", "name": "Automatic charge capture from notes", "description": "Charges auto-created from signed clinical notes: CPT from procedure documentation, E&M from visit documentation, nursing charges from vitals/injections", "source": "HealthTrack-Pro-BRD.md (FR-510)", "confidence": "high", "category": "billing"},
    {"id": "BR-022", "name": "Sliding fee scale for uninsured", "description": "Discount based on federal poverty level: 100% FPL = 100% discount, 200% FPL = 75% discount, etc.", "source": "HealthTrack-Pro-BRD.md (FR-513)", "confidence": "high", "category": "billing"},
    {"id": "BR-023", "name": "Denial management workflow", "description": "Categorize denial reason, assign to specialist, track appeal submission and outcome, report denial patterns by payer and reason", "source": "HealthTrack-Pro-BRD.md (FR-509)", "confidence": "high", "category": "billing"},
    {"id": "BR-024", "name": "Payment plan management", "description": "Configurable minimum payment, frequency, 0% interest under 12 months, auto-draft via stored payment method, delinquency workflow: reminder → warning → collections", "source": "HealthTrack-Pro-BRD.md (FR-506)", "confidence": "high", "category": "billing"},
    {"id": "BR-025", "name": "10-role RBAC model", "description": "System Admin, Physician, Nurse, MA, Front Desk, Billing Specialist, Lab Tech, Compliance Officer, Report Viewer, Patient (portal)", "source": "HealthTrack-Pro-BRD.md (FR-801)", "confidence": "high", "category": "security"},
    {"id": "BR-026", "name": "Break-the-glass emergency access", "description": "Emergency access with documented reason, logged and reported to compliance. Separate from normal access controls.", "source": "HealthTrack-Pro-BRD.md (FR-806)", "confidence": "high", "category": "security"},
    {"id": "BR-027", "name": "Comprehensive audit trail", "description": "Log all: user logins, patient record access (view/create/modify/delete/print/export), clinical note changes, billing transactions, configuration changes, permission changes", "source": "HealthTrack-Pro-BRD.md (FR-805)", "confidence": "high", "category": "security"},
    {"id": "BR-028", "name": "PHI column-level encryption", "description": "Beyond AES-256 at rest, PHI fields (SSN, clinical data) require additional column-level encryption in the database", "source": "HealthTrack-Pro-BRD.md (NFR-202)", "confidence": "high", "category": "security"},
    {"id": "BR-029", "name": "Data retention policy", "description": "Clinical records: 10 years from last encounter (NC state law). Billing records: 7 years (federal). Audit logs: 6 years (HIPAA).", "source": "Meeting Notes (Linda Park) + NFR-210", "confidence": "medium", "category": "compliance"},
    {"id": "BR-030", "name": "USCDI v3 patient data export", "description": "Patients must be able to download their complete medical records in USCDI v3 format per 21st Century Cures Act", "source": "HealthTrack-Pro-BRD.md (FR-606, NFR-206)", "confidence": "high", "category": "compliance"},
]

HEALTHTRACK_ENTITIES = [
    {"name": "Patient", "type": "core_entity", "attributes": ["patient_id", "legal_name", "preferred_name", "dob", "ssn_encrypted", "gender_identity", "biological_sex", "race", "ethnicity", "preferred_language", "active", "deceased"], "relationships": ["has many Appointments", "has many ClinicalNotes", "has many Medications", "has many Allergies", "has many InsuranceCoverages", "assigned to Physician"]},
    {"name": "Physician", "type": "actor", "attributes": ["physician_id", "name", "npi", "specialty", "dea_number", "license_state", "license_number"], "relationships": ["belongs to Clinic", "has many Appointments", "writes ClinicalNotes", "prescribes Medications"]},
    {"name": "Clinic", "type": "organization", "attributes": ["clinic_id", "name", "address", "phone", "fax", "npi", "tax_id", "operating_hours"], "relationships": ["has many Physicians", "has many Patients", "has many Rooms"]},
    {"name": "Appointment", "type": "transaction", "attributes": ["appointment_id", "date", "time", "duration", "type", "status", "reason", "room"], "relationships": ["belongs to Patient", "belongs to Physician", "has one ClinicalNote", "has one BillingClaim"]},
    {"name": "ClinicalNote", "type": "document", "attributes": ["note_id", "type", "date", "subjective", "objective", "assessment", "plan", "signed", "signed_date"], "relationships": ["belongs to Patient", "written by Physician", "linked to Appointment"]},
    {"name": "Medication", "type": "clinical", "attributes": ["medication_id", "drug_name", "dosage", "frequency", "route", "status", "refills_remaining", "ndc_code", "is_controlled"], "relationships": ["belongs to Patient", "prescribed by Physician"]},
    {"name": "Allergy", "type": "clinical", "attributes": ["allergy_id", "allergen", "reaction", "severity", "verified"], "relationships": ["belongs to Patient"]},
    {"name": "LabOrder", "type": "transaction", "attributes": ["order_id", "tests_ordered", "lab_company", "priority", "status", "clinical_indication"], "relationships": ["belongs to Patient", "ordered by Physician", "has many LabResults"]},
    {"name": "LabResult", "type": "clinical", "attributes": ["result_id", "test_name", "value", "unit", "reference_range", "abnormal_flag", "critical_flag"], "relationships": ["belongs to LabOrder", "reviewed by Physician"]},
    {"name": "BillingClaim", "type": "financial", "attributes": ["claim_id", "cpt_code", "icd_primary", "charges", "status", "denial_reason"], "relationships": ["belongs to Patient", "linked to Appointment", "submitted to InsurancePlan"]},
    {"name": "InsurancePlan", "type": "reference", "attributes": ["plan_id", "name", "payer_id", "type", "phone"], "relationships": ["covers many Patients"]},
    {"name": "InsuranceCoverage", "type": "junction", "attributes": ["coverage_id", "member_id", "group_number", "priority", "effective_date"], "relationships": ["links Patient to InsurancePlan"]},
    {"name": "User", "type": "actor", "attributes": ["user_id", "username", "role", "clinic_id", "active", "mfa_enabled"], "relationships": ["has one Role", "belongs to Clinic"]},
    {"name": "AuditLog", "type": "system", "attributes": ["log_id", "user_id", "patient_id", "action", "resource", "timestamp", "ip_address"], "relationships": ["belongs to User", "references Patient"]},
    {"name": "VitalSign", "type": "clinical", "attributes": ["vital_id", "height", "weight", "bmi", "bp_systolic", "bp_diastolic", "heart_rate", "temperature", "o2_sat", "pain_level"], "relationships": ["belongs to Patient", "linked to Appointment"]},
    {"name": "Document", "type": "storage", "attributes": ["document_id", "type", "name", "s3_key", "content_type", "file_size"], "relationships": ["belongs to Patient", "uploaded by User"]},
]

HEALTHTRACK_CONFLICTS = [
    {"id": "CON-001", "type": "data_conflict", "description": "Approval threshold inconsistency: BRD specifies $10,000 (FR-502) but legacy code implements $5,000 (BillingProcessor.THRESHOLD). Meeting notes suggest it may vary by department.", "severity": "blocking", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "legacy-patient-module.py + Meeting Notes"},
    {"id": "CON-002", "type": "compliance_conflict", "description": "Data retention period: BRD states 7 years for billing records (DM-103), but Linda Park cited NC GS § 90-210.25A requiring 10 years for clinical records. These are different categories but the BRD doesn't distinguish them clearly.", "severity": "blocking", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "Meeting Notes (Linda Park)"},
    {"id": "CON-003", "type": "implementation_gap", "description": "Duplicate detection: BRD requires probabilistic matching with weighted scoring (FR-109), but legacy code uses exact match only. The new system must implement the probabilistic algorithm.", "severity": "high", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "legacy-patient-module.py"},
    {"id": "CON-004", "type": "bug", "description": "Scheduling overlap: BRD requires preventing double-booking (FR-202), but legacy code only checks exact time matches, not duration overlaps. A 60-min appointment at 9:00 allows booking at 9:30.", "severity": "high", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "legacy-patient-module.py"},
    {"id": "CON-005", "type": "compliance_violation", "description": "Deleted CPT code still in use: Legacy code maps 'NEW_LOW' visits to CPT 99201, which was deleted by CMS in January 2021. Claims using this code will be automatically denied.", "severity": "high", "source_a": "CMS 2021 E&M Guidelines", "source_b": "legacy-patient-module.py"},
    {"id": "CON-006", "type": "security_critical", "description": "SSN stored in plaintext: 243,000 patient records have SSN as VARCHAR(11) with no encryption. This is a HIPAA violation and creates class-action liability in case of breach.", "severity": "blocking", "source_a": "HIPAA Security Rule", "source_b": "legacy-schema.sql"},
    {"id": "CON-007", "type": "security_critical", "description": "SQL injection vulnerabilities: sp_SearchPatients and PatientService.search() use string concatenation for queries. 34 ASP pages identified with same vulnerability.", "severity": "blocking", "source_a": "Security best practices", "source_b": "legacy-schema.sql + legacy-patient-module.py"},
    {"id": "CON-008", "type": "data_model", "description": "Gender representation: BRD requires gender identity capture (FR-101), but legacy schema uses CHAR(1) with only 'M' or 'F'.", "severity": "medium", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "legacy-schema.sql"},
    {"id": "CON-009", "type": "data_model", "description": "Date storage: Legacy stores DOB as VARCHAR(10) in 'MM/DD/YYYY' format. 12,400 records have invalid dates. Must convert to proper DATE type during migration.", "severity": "high", "source_a": "HealthTrack-Pro-BRD.md (DM-110)", "source_b": "legacy-schema.sql"},
    {"id": "CON-010", "type": "priority_conflict", "description": "Telehealth timeline: CMO wants video integration in Phase 1, VP Product placed it in Phase 2. Compromise reached but not documented.", "severity": "medium", "source_a": "Meeting Notes (Dr. Wright)", "source_b": "HealthTrack-Pro-BRD.md (Phase 2)"},
    {"id": "CON-011", "type": "access_control", "description": "Role model mismatch: BRD defines 10 roles (FR-801), legacy system has only 3 roles (Admin/Doctor/Staff). Billing staff currently can read clinical notes, violating HIPAA minimum necessary principle.", "severity": "blocking", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "legacy-schema.sql"},
    {"id": "CON-012", "type": "audit_gap", "description": "Audit trail scope: BRD requires record-level access logging (FR-805), legacy system only logs user logins. No way to detect unauthorized patient record access.", "severity": "blocking", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "Technical Specification (SEC-05)"},
    {"id": "CON-013", "type": "storage", "description": "Document storage: Legacy stores 890 GB of documents as BLOBs in database, causing 40% of database size. BRD implies cloud storage. Must extract to S3 during migration.", "severity": "high", "source_a": "HealthTrack-Pro-BRD.md", "source_b": "Technical Specification"},
]

HEALTHTRACK_QUESTIONS = [
    {"id": "Q-001", "question": "What is the correct approval threshold for high-dollar billing claims — $5,000 or $10,000? Should it vary by department or service type?", "impact": "Affects billing workflow design, authorization UI, and business rules engine configuration", "priority": "blocking"},
    {"id": "Q-002", "question": "Please confirm data retention requirements: 10 years for clinical records (NC GS § 90-210.25A) and 7 years for billing (federal)? Are there Virginia-specific requirements?", "impact": "Affects data archival strategy, storage cost projections, and compliance architecture", "priority": "blocking"},
    {"id": "Q-003", "question": "Is telehealth video integration confirmed for Phase 2? Should Phase 1 architecture accommodate video integration without rework?", "impact": "Affects infrastructure planning, third-party vendor selection, and Phase 1 scope", "priority": "high"},
    {"id": "Q-004", "question": "Which external systems beyond labs need integration? Specifically: hospital systems (Epic/Cerner), pharmacy dispensing, or health information exchanges (HIE)?", "impact": "Affects API architecture, integration middleware, and security boundary design", "priority": "high"},
    {"id": "Q-005", "question": "Will physicians use personal devices (BYOD) or clinic-provided devices? This affects MDM requirements and security architecture.", "impact": "Affects mobile strategy, device management, and security policies", "priority": "high"},
    {"id": "Q-006", "question": "Is the $1.2M budget inclusive of Year 1 AWS hosting costs (~$120K) or is hosting separate?", "impact": "Affects build vs buy decisions, infrastructure choices, and feature scope", "priority": "medium"},
    {"id": "Q-007", "question": "Should the patient portal support languages beyond English and Spanish?", "impact": "Affects i18n architecture, content translation scope, and language access compliance", "priority": "medium"},
    {"id": "Q-008", "question": "What disaster recovery requirements apply? BRD states 4-hour RTO and 1-hour RPO — should we design for active-active multi-AZ?", "impact": "Affects AWS architecture complexity and cost", "priority": "high"},
    {"id": "Q-009", "question": "Are there plans to expand beyond NC and VA? State-specific regulations may affect data model.", "impact": "Affects multi-state compliance architecture and data residency", "priority": "medium"},
    {"id": "Q-010", "question": "Should the system support international patients (non-US addresses, non-US phone formats, non-US insurance)?", "impact": "Affects address validation, phone formatting, and insurance data model", "priority": "low"},
]

HEALTHTRACK_UNDERSTANDING = {
    "purpose": "HealthTrack Pro is a comprehensive patient management system for a multi-clinic healthcare organization serving 47 clinics across NC and VA. It handles the complete patient lifecycle: registration, scheduling, clinical documentation, lab management, billing/claims, and patient engagement through a self-service portal.",
    "domain": "Healthcare / Ambulatory Care",
    "current_state": "Running on unsupported technology stack (Classic ASP, VB6, SQL Server 2008 R2) with critical security vulnerabilities including plaintext SSN storage, SQL injection risks, and no encryption.",
    "key_workflows": [
        "Patient registration with insurance verification and duplicate detection",
        "Appointment scheduling with conflict prevention across 8 calendar sources",
        "Clinical documentation with structured templates and co-signing workflows",
        "Lab order management with FHIR R4 integration to 3 external labs",
        "Billing and claims processing with real-time scrubbing and denial management",
        "Patient self-service portal with secure messaging and record access",
        "Controlled substance prescribing with PDMP integration",
        "Quality reporting for MIPS/MACRA and population health analytics",
    ],
    "critical_risks": [
        "HIPAA audit in September 2026 — encryption must be in place",
        "243,000 patient SSNs stored in plaintext — breach liability",
        "SQL injection vulnerabilities in 34+ pages — active exploit risk",
        "18% billing denial rate — $3.4M annual revenue loss",
        "47 departed employees with active system access",
        "No disaster recovery capability",
    ],
}

HEALTHTRACK_QUALITY = {"score": 88, "completeness": 92, "depth": 85, "consistency": 78, "traceability": 90, "actionability": 95}


def get_discover_data(scenario: str) -> dict:
    """Get the discovery output data for the detected scenario."""
    if scenario == "healthtrack":
        return {
            "business_rules": HEALTHTRACK_RULES,
            "domain_entities": HEALTHTRACK_ENTITIES,
            "conflicts": HEALTHTRACK_CONFLICTS,
            "clarification_questions": HEALTHTRACK_QUESTIONS,
            "system_understanding": HEALTHTRACK_UNDERSTANDING,
            "quality_assessment": HEALTHTRACK_QUALITY,
        }
    # Generic fallback
    return {
        "business_rules": HEALTHTRACK_RULES[:8],
        "domain_entities": HEALTHTRACK_ENTITIES[:6],
        "conflicts": HEALTHTRACK_CONFLICTS[:3],
        "clarification_questions": HEALTHTRACK_QUESTIONS[:5],
        "system_understanding": {"purpose": "System under analysis", "domain": "General", "key_workflows": [], "critical_risks": []},
        "quality_assessment": {"score": 75, "completeness": 70, "depth": 72, "consistency": 80, "traceability": 75, "actionability": 78},
    }


HEALTHTRACK_DESIGN = {
    "architecture": {
        "pattern": "microservices",
        "rationale": "HIPAA compliance requires service-level isolation for clinical, billing, and patient portal domains. Each service has its own database to enforce data access boundaries.",
        "adrs": [
            {"id": "ADR-001", "title": "React + Next.js frontend", "decision": "Mobile-responsive web app, not native. Staff use browser-based access, patients use responsive portal."},
            {"id": "ADR-002", "title": "Node.js/NestJS backend", "decision": "TypeScript for type safety, team familiarity, strong FHIR library ecosystem."},
            {"id": "ADR-003", "title": "PostgreSQL 16 with column-level encryption", "decision": "PHI fields (SSN, clinical data) encrypted at column level using pgcrypto. AES-256 at rest via AWS RDS."},
            {"id": "ADR-004", "title": "AWS ECS Fargate deployment", "decision": "HIPAA-eligible services. No server management. Auto-scaling per service."},
            {"id": "ADR-005", "title": "FHIR R4 clinical data model", "decision": "Standard clinical data representation. Enables interoperability with labs, hospitals, and HIEs."},
            {"id": "ADR-006", "title": "Event-driven with SQS", "decision": "Async processing for lab results, claims, reminders. Decouples services."},
            {"id": "ADR-007", "title": "Okta for identity management", "decision": "SSO, MFA, RBAC. HIPAA-compliant. Integrates with clinic Active Directory."},
            {"id": "ADR-008", "title": "8 microservices", "decision": "Patient, Scheduling, Clinical, Lab, Billing, Portal, Notification, Admin services."},
        ],
        "stack": [
            {"category": "Frontend", "technology": "React + Next.js 14"},
            {"category": "Backend", "technology": "Node.js + NestJS (TypeScript)"},
            {"category": "Database", "technology": "PostgreSQL 16 + pgcrypto"},
            {"category": "Cloud", "technology": "AWS (ECS Fargate, RDS, S3, SQS)"},
            {"category": "Auth", "technology": "Okta (SSO, MFA, RBAC)"},
            {"category": "Lab Integration", "technology": "FHIR R4 + HL7v2"},
            {"category": "E-Prescribing", "technology": "Surescripts (NCPDP)"},
            {"category": "Monitoring", "technology": "Datadog + PagerDuty"},
        ],
    },
    "database_schema": {
        "total_tables": 22,
        "tables": [
            {"name": "patients", "columns": 15, "purpose": "Core patient demographics with encrypted PHI"},
            {"name": "patient_addresses", "columns": 8, "purpose": "Multiple addresses per patient"},
            {"name": "insurance_coverages", "columns": 12, "purpose": "Patient insurance with priority ranking"},
            {"name": "physicians", "columns": 10, "purpose": "Provider directory with NPI and DEA"},
            {"name": "clinics", "columns": 9, "purpose": "Clinic locations and configuration"},
            {"name": "appointments", "columns": 14, "purpose": "Scheduling with conflict detection"},
            {"name": "clinical_notes", "columns": 12, "purpose": "SOAP notes with co-signing workflow"},
            {"name": "medications", "columns": 14, "purpose": "Prescriptions with controlled substance tracking"},
            {"name": "allergies", "columns": 7, "purpose": "Patient allergies with severity"},
            {"name": "vitals", "columns": 12, "purpose": "Vital signs with pediatric ranges"},
            {"name": "lab_orders", "columns": 10, "purpose": "Lab orders with FHIR integration"},
            {"name": "lab_results", "columns": 11, "purpose": "Results with critical value flagging"},
            {"name": "billing_claims", "columns": 16, "purpose": "Claims with real-time scrubbing"},
            {"name": "payments", "columns": 10, "purpose": "Patient payments with Stripe"},
            {"name": "payment_plans", "columns": 9, "purpose": "Installment plans with auto-draft"},
            {"name": "users", "columns": 12, "purpose": "System users with 10-role RBAC"},
            {"name": "roles", "columns": 5, "purpose": "Role definitions with permissions"},
            {"name": "audit_logs", "columns": 10, "purpose": "Record-level access logging for HIPAA"},
            {"name": "consent_records", "columns": 8, "purpose": "5 consent types with versioning"},
            {"name": "documents", "columns": 8, "purpose": "S3 references (not BLOBs)"},
            {"name": "waitlist_entries", "columns": 7, "purpose": "Waitlist with 2-hour confirmation window"},
            {"name": "referrals", "columns": 9, "purpose": "Referral tracking with NPI verification"},
        ],
    },
    "api_specification": {
        "total_endpoints": 45,
        "endpoints": [
            {"method": "POST", "path": "/patients", "domain": "Patient"},
            {"method": "GET", "path": "/patients/{id}", "domain": "Patient"},
            {"method": "POST", "path": "/patients/{id}/insurance", "domain": "Patient"},
            {"method": "POST", "path": "/patients/search", "domain": "Patient"},
            {"method": "POST", "path": "/appointments", "domain": "Scheduling"},
            {"method": "GET", "path": "/appointments/availability", "domain": "Scheduling"},
            {"method": "POST", "path": "/appointments/{id}/checkin", "domain": "Scheduling"},
            {"method": "POST", "path": "/clinical-notes", "domain": "Clinical"},
            {"method": "POST", "path": "/clinical-notes/{id}/sign", "domain": "Clinical"},
            {"method": "POST", "path": "/prescriptions", "domain": "Clinical"},
            {"method": "POST", "path": "/lab-orders", "domain": "Lab"},
            {"method": "GET", "path": "/lab-results/{id}", "domain": "Lab"},
            {"method": "POST", "path": "/billing/claims", "domain": "Billing"},
            {"method": "POST", "path": "/billing/claims/{id}/scrub", "domain": "Billing"},
            {"method": "POST", "path": "/payments", "domain": "Billing"},
        ],
    },
    "auth_design": {"strategy": "Okta SSO + JWT", "roles": 10, "permissions": 45, "mfa": "Required for all clinical users"},
    "frontend_design": {"framework": "Next.js 14", "pages": 18, "components": 45, "state_management": "React Query + Zustand"},
    "quality_assessment": {"score": 85, "completeness": 90, "consistency": 82, "feasibility": 88, "traceability": 85, "security": 80},
}


def get_design_data(scenario: str) -> dict:
    """Get the design output data for the detected scenario."""
    if scenario == "healthtrack":
        return HEALTHTRACK_DESIGN
    # Generic fallback
    return {
        "architecture": {"pattern": "modular_monolith", "rationale": "Best fit for team and timeline", "adrs": [], "stack": [{"category": "Backend", "technology": "FastAPI"}, {"category": "Frontend", "technology": "Next.js"}, {"category": "Database", "technology": "PostgreSQL"}]},
        "database_schema": {"total_tables": 10, "tables": [{"name": "users", "columns": 8, "purpose": "User accounts"}]},
        "api_specification": {"total_endpoints": 20, "endpoints": []},
        "auth_design": {"strategy": "JWT", "roles": 4, "permissions": 16},
        "frontend_design": {"framework": "Next.js 14", "pages": 8, "components": 20},
        "quality_assessment": {"score": 78, "completeness": 75, "consistency": 80, "feasibility": 85, "traceability": 70, "security": 75},
    }
