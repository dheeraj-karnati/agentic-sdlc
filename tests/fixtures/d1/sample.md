# Project Requirements

## Overview

This document describes the requirements for the Patient Portal system.
The system allows patients to view their medical records and schedule appointments.

## Key Features

- Online appointment scheduling
- Medical record access
- Prescription refill requests
- Secure messaging with providers

## Data Model

| Entity | Description | Key Fields |
|--------|-------------|------------|
| Patient | Registered user | name, dob, email |
| Appointment | Scheduled visit | date, provider, status |
| Prescription | Medication order | drug, dosage, refills |

## Business Rules

Patients must verify their identity before accessing records.
Appointments can only be scheduled during business hours (8am-5pm).
Prescriptions with zero refills require provider approval for renewal.
