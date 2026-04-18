# D8X Demo Simulation Data Guide
# Use this to configure simulate_discover and simulate_design functions
# for each demo scenario

---

## SCENARIO 1: Legacy HealthTrack (8 files)

### Files included
1. 01-HealthTrack-Pro-BRD.md (requirements - 120+ FRs, 20+ NFRs)
2. 02-Technical-Specification.md (legacy stack, 15 security issues)
3. 03-Meeting-Notes-Kickoff.md (stakeholder priorities, conflicts)
4. 04-legacy-schema.sql (14 tables, vulnerabilities)
5. 05-legacy-patient-module.py (3 classes, bugs, SQL injection)
6. 06-HIPAA-Compliance-Checklist.md (30 compliance gaps)
7. 07-Billing-Workflow-Current.md (denial analysis, revenue impact)
8. 08-Data-Migration-Analysis.md (data quality issues, migration plan)

### D1: Ingest expected output
- 8 files processed
- File types: 5 documents, 1 SQL schema, 1 Python code, 1 compliance doc
- Total words: ~18,000
- Project type: legacy_modernization (code detected)
- Quality score: 92 (high diversity, high volume, code present)
- Suggestions: none (comprehensive set)

### D2: Discover expected output — LARGE SCALE

#### Business Rules (target: 120+ for demo impact)
Extract from BRD functional requirements. Each FR-xxx becomes 1-3 rules.
Key categories:

Patient Registration (25 rules):
- BR-001: New patient requires demographics + insurance + emergency contacts
- BR-002: Insurance eligibility must be verified real-time via EDI 270/271
- BR-003: Duplicate detection uses probabilistic matching (75% review, 90% block)
- BR-004: Patient merge requires audit trail of before/after values
- BR-005: Patient photo required for identity verification at check-in
- BR-006: Self-registration via kiosk captures demographics + insurance photo + consent
- BR-007: Workers comp cases require employer information
- BR-008: Referral requires NPI lookup verification
- BR-009: Record inactivation requires reason code
- BR-010: All demographic changes tracked with before/after + timestamp + user
- BR-011: Consent management: treatment, HIPAA, data sharing, telehealth, research
- BR-012: Social determinants captured using LOINC-coded assessments
- BR-013: Pharmacy lookup via NCPDP integration
- BR-014: Special needs flags: interpreter, mobility, behavioral, legal guardian
- BR-015: Multiple addresses per patient with date ranges for temporary
- BR-016: Unlimited phone numbers with contact preference per HIPAA
- BR-017: Email consent independently togglable per communication type
- BR-018: Minimum 2 emergency contacts required per patient
- BR-019: Insurance card image capture (front + back)
- BR-020: Preferred name separate from legal name
- BR-021: Gender identity captured separately from biological sex
- BR-022: Race/ethnicity captured (currently free-text, must be coded)
- BR-023: Preferred language from ISO 639 list
- BR-024: Primary physician assignment required
- BR-025: Deceased status tracking with date

Scheduling (30 rules):
- BR-026 through BR-055 (from FR-201 through FR-220)
- Key rules: double-booking prevention (cross-reference 8 calendars), appointment types with durations, reminder sequences, self-scheduling rules, waitlist with 2-hour confirm window, recurring appointments, walk-in queue with wait time calculation, multi-provider visits, no-show policy (warning→deposit→dismissal), check-in methods (4 options), overbooking limits, template management, payer-specific scheduling rules, resource scheduling

Clinical Documentation (30 rules):
- BR-056 through BR-085 (from FR-301 through FR-320)
- Key rules: 9 note template types, voice dictation, ICD-10 problem list, drug interaction checking (5 types), allergy severity levels, vital sign validation with pediatric charts, clinical decision support alerts, order entry types, e-prescribing NCPDP standard, EPCS two-factor auth, controlled substance PDMP check, cosigning workflow, addendum without modification, immunization registry submission, flowsheets for chronic disease, after-visit summary in plain language

Lab Integration (12 rules):
- BR-086 through BR-097 (from FR-401 through FR-412)
- Key rules: FHIR R4 bidirectional for LabCorp + Quest, REST for BioReference, automatic result matching, configurable reference ranges, critical result paging with escalation (15min→30min), result acknowledgment tracking, LOINC coding, point-of-care results, panel ordering

Billing (16 rules):
- BR-098 through BR-113 (from FR-501 through FR-516)
- Key rules: NLP-based CPT suggestion, real-time claim scrubbing (6 checks), EDI 837P/I, ERA auto-posting, patient responsibility estimation, payment plans, Stripe integration, aging reports, denial workflow, charge capture from notes, sliding fee scale, prior auth tracking, credentialing tracking, financial KPIs

Patient Portal (16 rules):
- BR-114 through BR-129 (from FR-601 through FR-616)
- Key rules: MFA with biometric option, lab results with plain language, refill requests, secure messaging with 48hr SLA, USCDI v3 download, online payment, health education linked to diagnoses, proxy access with age-18 expiration, pre-visit questionnaires, telehealth launch, document upload, care plan summaries

Administration (10 rules):
- BR-130 through BR-139 (from FR-801 through FR-810)
- Key rules: 10 RBAC roles, user provisioning workflow, password policy (14 chars), SSO via SAML/OIDC, comprehensive audit logging, break-the-glass access, configurable session timeout, clinic management, fee schedule management

Security/Compliance (15 rules from NFRs):
- BR-140 through BR-154
- Key rules: AES-256 encryption at rest, column-level PHI encryption, HIPAA Security Rule, Privacy Rule, HITECH breach notification, 21st Century Cures Act, annual pen testing, quarterly vuln scanning, BAA requirements, data retention (10yr clinical, 7yr billing), WCAG 2.1 AA, Section 508, multi-language support

#### Domain Entities (target: 45+)

Core Clinical:
Patient, Physician, Clinic, Appointment, ClinicalNote, Medication, Allergy, VitalSign, LabOrder, LabResult, Immunization, Problem (Diagnosis), Referral, ClinicalImage

Scheduling:
AppointmentType, AppointmentTemplate, WaitlistEntry, RecurringSchedule, Room, Equipment, StaffAssignment, ScheduleBlock (surgical, PTO, on-call)

Billing/Financial:
InsurancePlan, BillingClaim, Payment, PaymentPlan, ERA, DenialAppeal, FeeSchedule, PriorAuthorization, Credential, Superbill

Portal:
PatientPortalUser, SecureMessage, PreVisitQuestionnaire, HealthEducationResource, CarePlan, ProxyAccess

Administrative:
User, Role, Permission, AuditLog, EmergencyAccess, Announcement, ConsentRecord, Document

Integration:
HL7Message, FHIRResource, SurescriptsTransaction, PDMPQuery, ImmunizationRegistrySubmission, DirectSecureMessage

#### Conflicts (target: 15-20)

Deliberate conflicts planted across documents:

| # | Conflict | Source A | Source B | Severity |
|---|----------|----------|----------|----------|
| 1 | Approval threshold: $10,000 vs $5,000 | BRD (FR-502) | Code (BillingProcessor.THRESHOLD) + Meeting notes (Robert) | BLOCKING |
| 2 | Data retention: 7 years vs 10 years | BRD (DM-103) | Meeting notes (Linda Park: NC GS § 90-210.25A) | BLOCKING |
| 3 | Duplicate detection: probabilistic vs exact match | BRD (FR-109) | Code (PatientService.check_duplicate) | HIGH |
| 4 | Scheduling conflict: checks time only, not duration | BRD (FR-202) | Code (AppointmentScheduler.book) | HIGH |
| 5 | CPT code 99201 used but deleted in 2021 | Code (BillingProcessor.CPT_MAP) | Current CMS guidelines | HIGH |
| 6 | Password policy: BRD says 14 chars, HIPAA checklist says "no requirements" currently | BRD (FR-803) | HIPAA Checklist | MEDIUM |
| 7 | Session timeout: BRD says 15 min, tech spec says current is "indefinite" | BRD (FR-807) | Tech Spec (SEC-08) | MEDIUM |
| 8 | User roles: BRD defines 10 roles, legacy system has 3 | BRD (FR-801) | Schema (users.role) | HIGH |
| 9 | Telehealth: Dr. Wright wants Phase 1, Sarah says Phase 2 | Meeting notes (debate) | BRD (Phase 2 list) | MEDIUM |
| 10 | Lab integration: BRD says FHIR R4, BioReference uses REST | BRD (FR-401) | BRD (FR-403) | LOW |
| 11 | Audit trail: BRD requires record-level, system logs login only | BRD (FR-805) | Tech Spec (SEC-05) | BLOCKING |
| 12 | Encryption: BRD says AES-256, current system has none | BRD (NFR-201) | Tech Spec (SEC-04) | BLOCKING |
| 13 | Error handling: BRD implies graceful handling, code uses On Error Resume Next | BRD (implied) | Tech Spec (debt #7) | HIGH |
| 14 | Gender: BRD captures gender identity, schema has CHAR(1) M/F only | BRD (FR-101) | Schema (patients.gender) | MEDIUM |
| 15 | Date storage: BRD implies proper dates, schema uses VARCHAR | BRD (DM-110) | Schema (patients.dob) | HIGH |
| 16 | Document storage: BRD implies cloud, legacy uses DB BLOBs | BRD (implied) | Schema (patient_documents) | HIGH |

#### Clarification Questions (target: 10-15)

| # | Question | Impact | Priority |
|---|----------|--------|----------|
| 1 | What is the correct approval threshold — $5,000 or $10,000? Is it per-department? | Affects billing workflow, authorization logic, and UI | BLOCKING |
| 2 | Confirm data retention: 10 years clinical (NC law) and 7 years billing (federal)? | Affects archive strategy, storage costs, and compliance | BLOCKING |
| 3 | Which external systems need integration beyond labs? (Epic/Cerner hospital, pharmacy systems?) | Affects architecture scope and timeline | HIGH |
| 4 | Is telehealth video in Phase 1 or Phase 2? Meeting showed disagreement. | Affects architecture planning and third-party selection | HIGH |
| 5 | Should the patient portal support languages beyond English and Spanish? What % of patients are non-English? | Affects i18n architecture scope | MEDIUM |
| 6 | Are there any state-specific regulations for Virginia that differ from North Carolina? | Affects compliance implementation per state | HIGH |
| 7 | What is the disaster recovery RTO/RPO target? BRD says 4hr RTO/1hr RPO — is this confirmed? | Affects infrastructure architecture and cost | HIGH |
| 8 | Will physicians use personal devices (BYOD) or clinic-provided devices? | Affects MDM, security architecture, app distribution | HIGH |
| 9 | Is the $1.2M budget inclusive of ongoing AWS hosting costs or just migration? | Affects build vs. buy decisions and infrastructure choices | MEDIUM |
| 10 | How many concurrent telehealth sessions should the system support? | Affects video infrastructure sizing | MEDIUM |
| 11 | Should the system support international patients (non-US addresses, non-US insurance)? | Affects data model and validation rules | LOW |
| 12 | Is there a preferred e-prescribing vendor or should we evaluate options? | Affects Surescripts integration approach | MEDIUM |

### D3: Design expected output

Architecture Decisions (8 ADRs):
- ADR-001: React + Next.js frontend (mobile-responsive, not native app)
- ADR-002: Node.js/NestJS backend (TypeScript, team familiarity)
- ADR-003: PostgreSQL 16 with column-level encryption for PHI
- ADR-004: AWS deployment (ECS Fargate, RDS, S3, CloudFront)
- ADR-005: FHIR R4 as primary clinical data model
- ADR-006: Event-driven architecture with SQS for async processing
- ADR-007: Okta for identity management (SSO, MFA, RBAC)
- ADR-008: Microservices for clinical, scheduling, billing, portal domains

Database Design (22 tables):
- patients (with encrypted SSN, proper date types, gender identity)
- patient_addresses, patient_phones, patient_contacts
- insurance_coverages (multiple per patient)
- physicians, clinics, rooms, equipment
- appointments, appointment_templates, waitlist_entries
- clinical_notes, note_templates
- medications, allergies, vitals, problems
- lab_orders, lab_results, lab_result_values
- billing_claims, payments, payment_plans
- users, roles, permissions, audit_logs
- documents (S3 references, not BLOBs)

API Design (45 endpoints across 8 domains)

Component Design (12 major UI components)

---

## SCENARIO 2: Greenfield FinPay (5 files)

### Files included
1. 01-FinPay-PRD.md (product requirements - 80+ requirements)
2. 02-FinPay-Technical-Architecture.md (microservices, event sourcing)
3. 03-FinPay-User-Stories-Sample.md (3 epics, 7 stories with ACs)
4. 04-FinPay-API-Design.md (endpoint catalog, error format)
5. 05-FinPay-Compliance-Requirements.md (PCI, KYC, AML, state licensing)

### D1: Ingest expected output
- 5 files processed
- File types: 5 documents (no code — greenfield)
- Total words: ~8,000
- Project type: greenfield (no code detected)
- Quality score: 78 (good volume, but no code, no meetings, no schema)
- Suggestions: "Consider adding technical diagrams, wireframes, or competitor analysis"

### D2: Discover expected output

#### Business Rules (target: 80+)

Payment Processing (20 rules):
- BR-001 through BR-020 from PAY-1xx requirements
- Key: tokenized card vault, ACH with Plaid, wire transfers, Apple/Google Pay, recurring billing, payment links, invoicing, payment splitting, 3DS 2.0, idempotency, smart retry, multi-currency

Money Movement (10 rules):
- BR-021 through BR-030 from MOV-1xx
- Key: payout schedules, holds, multi-party settlement, reserves, cross-border, 1099 reporting, negative balance recovery

Accounts (8 rules):
- BR-031 through BR-038 from ACC-1xx
- Key: FBO accounts, double-entry ledger, real-time balances, multi-currency, interest-bearing, sub-accounts

Risk & Compliance (15 rules):
- BR-039 through BR-053 from RSK-1xx
- Key: ML fraud scoring, velocity checks, AVS/CVV, chargeback management, KYC/KYB tiered levels, OFAC screening, PCI Level 1, SOC 2, AML monitoring, device fingerprinting

Integration (10 rules):
- BR-054 through BR-063 from INT-1xx
- Key: REST + GraphQL, 7 SDKs, webhooks with HMAC + retry, embeddable components, OAuth 2.0, sandbox environment, API versioning, rate limiting

Platform Dashboard (8 rules):
- BR-064 through BR-071 from DSH-1xx

Compliance (12 rules):
- BR-072 through BR-083 from compliance doc
- Key: FinCEN MSB, BSA, PATRIOT Act CIP, OFAC, 1099-K, state MTL, PCI DSS, GDPR, PSD2

#### Domain Entities (target: 35+)

Core: Merchant, Payment, PaymentMethod, Payout, Account, Transaction, JournalEntry
Risk: RiskScore, VelocityRule, Dispute, DisputeEvidence
Identity: KYCApplication, KYBApplication, BeneficialOwner, VerificationDocument
Configuration: Platform, APIKey, Webhook, WebhookDelivery, RateLimitRule
Financial: FeeSchedule, Reserve, Settlement, Reconciliation, TaxReport
Compliance: SanctionsScreening, SARReport, AuditLog

#### Conflicts (target: 5-8)
| # | Conflict | Source A | Source B | Severity |
|---|----------|----------|----------|----------|
| 1 | Card data handling: PRD says "tokenized card vault" (PAY-101) but also says "PCI cardholder data never touches FinPay servers" (compliance) — which is it? | PRD | Compliance | HIGH |
| 2 | API versioning: PRD says "12-month deprecation notice" (INT-107) but no migration strategy defined | PRD | Architecture | MEDIUM |
| 3 | KYC levels: PRD doesn't mention tiered verification but compliance doc defines 3 levels | PRD | Compliance | HIGH |
| 4 | Rate limiting: PRD says 1000/min (INT-108) but architecture doc says "configurable per platform" — what's the max? | PRD | Architecture | LOW |
| 5 | Data residency: GDPR requires EU data to stay in EU, but architecture shows single-region AWS deployment | Compliance (GDPR) | Architecture | BLOCKING |
| 6 | Chargeback threshold: architecture mentions monitoring at 0.9% but no automated merchant suspension defined | Architecture | Missing requirement | HIGH |
| 7 | Event sourcing: architecture says append-only, but GDPR requires right to erasure — contradiction | Architecture | Compliance | BLOCKING |

#### Clarification Questions (target: 8)
| # | Question | Impact | Priority |
|---|----------|--------|----------|
| 1 | How do you handle GDPR right-to-erasure with event sourcing (append-only)? Crypto-shredding? | Affects core data architecture | BLOCKING |
| 2 | What is the target for PCI DSS Level 1 audit timeline? | Affects security architecture decisions | HIGH |
| 3 | Which sponsor bank will you use (Column, Evolve, other)? Their requirements affect the architecture. | Affects compliance, API design, settlement | HIGH |
| 4 | What is the initial geographic scope? US-only or international from day 1? | Affects currency, compliance, infrastructure | HIGH |
| 5 | Should the ledger support real-time or near-real-time balance computation? | Affects database and caching architecture | HIGH |
| 6 | Is GraphQL API a day-1 requirement or future phase? | Affects API development scope | MEDIUM |
| 7 | What is the target transaction throughput for year 1? (Affects infrastructure sizing) | Affects architecture scale decisions | MEDIUM |
| 8 | Will you build the fraud ML model in-house or use a vendor (Sardine, Unit21)? | Affects build vs buy for risk service | HIGH |

### D3: Design expected output for FinPay

Architecture (event-driven microservices as described in their arch doc, validated against requirements):
- 12 microservices
- Kafka event backbone
- PostgreSQL + ClickHouse
- API Gateway with rate limiting

Database Design (18 tables across services):
- merchants, merchant_owners, verification_documents
- payments, payment_methods, refunds
- payouts, payout_items
- accounts, journal_entries, account_balances
- risk_scores, velocity_rules, disputes
- webhooks, webhook_deliveries, api_keys
- audit_logs

API Design (35 endpoints, validated against PRD)

---

## HOW TO USE THIS DATA

### For simulate_discover function:
1. Read the project_type from D1 output (legacy_modernization or greenfield)
2. Based on project_type, load the corresponding rule set above
3. Return rules, entities, conflicts, and questions as structured output
4. Update task progress every 3-5 seconds so the UI shows real-time work

### For simulate_design function:
1. Read D2 output from business_context store
2. Generate ADRs referencing specific business rules
3. Generate database schema addressing data issues found in D2
4. Generate API endpoints covering all functional requirements
5. Quality gate: verify every business rule has a corresponding design element

### For a compelling demo:
- Use the Legacy HealthTrack scenario (8 files, more conflicts, more drama)
- The conflicts are real-world problems that CTOs recognize immediately
- The approval threshold conflict ($5K vs $10K) always gets a reaction
- The SSN-in-plaintext finding makes compliance officers sit up straight
- The 18% denial rate → 5% target gives billing managers a clear ROI story
