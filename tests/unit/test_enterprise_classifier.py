"""Tests for enterprise file classifier."""

import pytest

from src.agents.ingest.skills.enterprise_classifier_skill import (
    AnalysisTier,
    ClassifiedFile,
    FileRole,
    classify_file,
    classify_files,
)


# ─── Java classification ───


class TestJavaClassification:
    def test_controller_by_path(self):
        r = classify_file("src/main/java/com/acme/controller/PatientController.java")
        assert r.role == FileRole.CONTROLLER
        assert r.tier == 1
        assert r.language == "java"

    def test_controller_by_name(self):
        r = classify_file("src/main/java/com/acme/PatientController.java")
        assert r.role == FileRole.CONTROLLER

    def test_servlet(self):
        r = classify_file("src/main/java/com/acme/web/LoginServlet.java")
        assert r.role == FileRole.CONTROLLER

    def test_service_by_path(self):
        r = classify_file("src/main/java/com/acme/service/BillingService.java")
        assert r.role == FileRole.SERVICE
        assert r.tier == 1

    def test_service_impl(self):
        r = classify_file("src/main/java/com/acme/service/BillingServiceImpl.java")
        assert r.role == FileRole.SERVICE

    def test_entity_by_path(self):
        r = classify_file("src/main/java/com/acme/entity/Patient.java")
        assert r.role == FileRole.ENTITY
        assert r.tier == 2

    def test_model_by_path(self):
        r = classify_file("src/main/java/com/acme/model/Invoice.java")
        assert r.role == FileRole.ENTITY

    def test_repository_by_name(self):
        r = classify_file("src/main/java/com/acme/PatientRepository.java")
        assert r.role == FileRole.REPOSITORY
        assert r.tier == 2

    def test_dao_by_name(self):
        r = classify_file("src/main/java/com/acme/dao/PatientDao.java")
        assert r.role == FileRole.REPOSITORY

    def test_dto_by_path(self):
        r = classify_file("src/main/java/com/acme/dto/PatientDTO.java")
        assert r.role == FileRole.DTO
        assert r.tier == 3

    def test_test_by_path(self):
        r = classify_file("src/test/java/com/acme/service/BillingServiceTest.java")
        assert r.role == FileRole.TEST
        assert r.tier == 3

    def test_util_by_name(self):
        r = classify_file("src/main/java/com/acme/util/StringUtils.java")
        assert r.role == FileRole.UTIL
        assert r.tier == 3

    def test_config_application_properties(self):
        r = classify_file("src/main/resources/application.properties")
        assert r.role == FileRole.CONFIG
        assert r.tier == 1

    def test_config_application_yml(self):
        r = classify_file("src/main/resources/application.yml")
        assert r.role == FileRole.CONFIG

    def test_pom_xml(self):
        r = classify_file("pom.xml")
        assert r.role == FileRole.BUILD_FILE
        assert r.tier == 2

    def test_build_gradle(self):
        r = classify_file("build.gradle")
        assert r.role == FileRole.BUILD_FILE

    def test_jsp_view(self):
        r = classify_file("src/main/webapp/WEB-INF/views/patient.jsp")
        assert r.role == FileRole.VIEW

    def test_java_package_extraction(self):
        r = classify_file("src/main/java/com/acme/billing/service/InvoiceService.java")
        assert r.package_path == "com.acme.billing.service"
        assert r.group_key == "com.acme.billing"

    def test_weblogic_config(self):
        r = classify_file("src/main/resources/weblogic-ejb-jar.xml")
        assert r.role == FileRole.CONFIG

    def test_websphere_config(self):
        r = classify_file("src/main/resources/ibm-web-bnd.xml")
        assert r.role == FileRole.CONFIG


# ─── COBOL classification ───


class TestCobolClassification:
    def test_cobol_program(self):
        r = classify_file("src/programs/BILLING.cbl")
        assert r.role == FileRole.SERVICE
        assert r.language == "cobol"
        assert r.tier == 1

    def test_cobol_cob_extension(self):
        r = classify_file("PAYROLL.cob")
        assert r.role == FileRole.SERVICE
        assert r.language == "cobol"

    def test_copybook(self):
        r = classify_file("copylib/CUSTCPY.cpy")
        assert r.role == FileRole.COPYBOOK
        assert r.language == "cobol_copybook"
        assert r.tier == 2

    def test_jcl(self):
        r = classify_file("jcl/NIGHTRUN.jcl")
        assert r.role == FileRole.JCL
        assert r.language == "jcl"
        assert r.tier == 2

    def test_jcl_proc(self):
        r = classify_file("procs/BILLING.proc")
        assert r.role == FileRole.JCL


# ─── PL/SQL classification ───


class TestPlsqlClassification:
    def test_package_spec(self):
        r = classify_file("db/packages/PKG_BILLING.pks")
        assert r.role == FileRole.STORED_PROCEDURE
        assert r.language == "plsql"
        assert r.tier == 1

    def test_package_body(self):
        r = classify_file("db/packages/PKG_BILLING.pkb")
        assert r.role == FileRole.STORED_PROCEDURE

    def test_trigger(self):
        r = classify_file("db/triggers/TRG_AUDIT.trg")
        assert r.role == FileRole.STORED_PROCEDURE

    def test_sql_view(self):
        r = classify_file("db/views/VW_PATIENT_SUMMARY.vw")
        assert r.role == FileRole.VIEW


# ─── Progress 4GL classification ───


class TestProgress4glClassification:
    def test_procedure(self):
        r = classify_file("src/billing/inv-calc.p")
        assert r.role == FileRole.SERVICE
        assert r.language == "progress_4gl"
        assert r.tier == 1

    def test_window(self):
        r = classify_file("src/ui/patient-search.w")
        assert r.role == FileRole.VIEW
        assert r.language == "progress_4gl"

    def test_include(self):
        r = classify_file("src/includes/common.i")
        assert r.role == FileRole.COPYBOOK
        assert r.language == "progress_include"

    def test_class(self):
        r = classify_file("src/billing/InvoiceProcessor.cls")
        assert r.role == FileRole.SERVICE
        assert r.language == "progress_class"


# ─── VB6 / Classic ASP classification ───


class TestVb6Classification:
    def test_vb6_module(self):
        r = classify_file("src/modules/BillingCalc.bas")
        assert r.role == FileRole.SERVICE
        assert r.language == "vb6"

    def test_vb6_form(self):
        r = classify_file("src/forms/PatientEntry.frm")
        assert r.role == FileRole.SERVICE
        assert r.language == "vb6"

    def test_asp_page(self):
        r = classify_file("pages/login.asp")
        assert r.role == FileRole.CONTROLLER
        assert r.language == "asp_classic"


# ─── Documentation classification ───


class TestDocumentationClassification:
    def test_markdown(self):
        r = classify_file("docs/BRD.md")
        assert r.role == FileRole.DOCUMENTATION
        assert r.tier == 1

    def test_pdf(self):
        r = classify_file("requirements/Technical-Spec.pdf")
        assert r.role == FileRole.DOCUMENTATION

    def test_docx(self):
        r = classify_file("docs/Meeting-Notes.docx")
        assert r.role == FileRole.DOCUMENTATION

    def test_xlsx(self):
        r = classify_file("data/test-cases.xlsx")
        assert r.role == FileRole.DOCUMENTATION


# ─── SQL migration classification ───


class TestMigrationClassification:
    def test_flyway(self):
        r = classify_file("db/migration/V001__create_tables.sql")
        assert r.role == FileRole.MIGRATION
        assert r.tier == 2

    def test_migration_directory(self):
        r = classify_file("src/main/resources/db/migration/V002__add_index.sql")
        assert r.role == FileRole.MIGRATION


# ─── Batch classification ───


class TestBatchClassification:
    def test_classify_files(self):
        paths = [
            "src/main/java/com/acme/service/BillingService.java",
            "src/test/java/com/acme/service/BillingServiceTest.java",
            "docs/BRD.md",
            "pom.xml",
        ]
        results = classify_files(paths)
        assert len(results) == 4
        assert results[0].role == FileRole.SERVICE
        assert results[1].role == FileRole.TEST
        assert results[2].role == FileRole.DOCUMENTATION
        assert results[3].role == FileRole.BUILD_FILE

    def test_tier_distribution(self):
        """Simulate a typical Java project and verify tier distribution."""
        paths = [
            # Tier 1 (services, controllers, config, docs)
            "src/main/java/com/acme/controller/PatientController.java",
            "src/main/java/com/acme/service/BillingService.java",
            "src/main/resources/application.yml",
            "docs/BRD.md",
            # Tier 2 (entities, repos)
            "src/main/java/com/acme/entity/Patient.java",
            "src/main/java/com/acme/repository/PatientRepository.java",
            "pom.xml",
            # Tier 3 (tests, DTOs, utils)
            "src/test/java/com/acme/BillingServiceTest.java",
            "src/main/java/com/acme/dto/PatientDTO.java",
            "src/main/java/com/acme/util/StringUtils.java",
        ]
        results = classify_files(paths)
        tier1 = [r for r in results if r.tier == 1]
        tier2 = [r for r in results if r.tier == 2]
        tier3 = [r for r in results if r.tier == 3]
        assert len(tier1) == 4
        assert len(tier2) == 3
        assert len(tier3) == 3
