"""Tests for package grouping skill."""

from src.agents.ingest.skills.code_structure_skill import CodeStructure, MethodSignature
from src.agents.ingest.skills.enterprise_classifier_skill import (
    ClassifiedFile,
    FileRole,
    classify_file,
)
from src.agents.ingest.skills.package_grouping_skill import (
    GroupingSummary,
    build_group_content,
    build_tier3_summary,
    group_files,
)


def _make_classified(path: str) -> ClassifiedFile:
    """Helper to classify a file path."""
    return classify_file(path)


class TestGroupFiles:
    def test_tier_separation(self):
        files = [
            _make_classified("src/main/java/com/acme/service/BillingService.java"),  # T1
            _make_classified("src/main/java/com/acme/entity/Patient.java"),  # T2
            _make_classified("src/test/java/com/acme/BillingServiceTest.java"),  # T3
            _make_classified("docs/BRD.md"),  # T1
        ]
        result = group_files(files)
        assert len(result.tier1_files) == 2  # service + doc
        assert len(result.tier2_groups) >= 1  # entity group
        assert len(result.tier3_files) == 1  # test

    def test_java_package_grouping(self):
        files = [
            _make_classified("src/main/java/com/acme/billing/entity/Invoice.java"),
            _make_classified("src/main/java/com/acme/billing/entity/LineItem.java"),
            _make_classified("src/main/java/com/acme/billing/entity/Payment.java"),
            _make_classified("src/main/java/com/acme/patient/entity/Patient.java"),
            _make_classified("src/main/java/com/acme/patient/entity/Address.java"),
        ]
        result = group_files(files)
        # Should create 2 groups: com.acme.billing and com.acme.patient
        assert len(result.tier2_groups) >= 2
        group_keys = {g.group_key for g in result.tier2_groups}
        assert any("billing" in k for k in group_keys)
        assert any("patient" in k for k in group_keys)

    def test_large_group_split(self):
        # Create 25 files in one package (exceeds MAX_GROUP_SIZE=20)
        files = [
            _make_classified(f"src/main/java/com/acme/model/Entity{i}.java")
            for i in range(25)
        ]
        result = group_files(files)
        # Should be split into 2 groups
        assert len(result.tier2_groups) >= 2

    def test_tier3_summary(self):
        files = [
            _make_classified("src/test/java/com/acme/ATest.java"),
            _make_classified("src/test/java/com/acme/BTest.java"),
            _make_classified("src/main/java/com/acme/dto/PatientDTO.java"),
            _make_classified("src/main/java/com/acme/util/StringUtils.java"),
        ]
        result = group_files(files)
        assert sum(result.tier3_summary.values()) == 4
        assert result.tier3_summary.get("test", 0) >= 2

    def test_code_structures_attached(self):
        files = [_make_classified("src/main/java/com/acme/entity/Patient.java")]
        structures = {
            "Patient.java": CodeStructure(
                language="java",
                class_name="Patient",
                methods=[MethodSignature(name="getName", return_type="String")],
            ),
        }
        result = group_files(files, code_structures=structures)
        assert len(result.tier2_groups) >= 1
        group = result.tier2_groups[0]
        assert group.files[0].code_structure is not None
        assert group.files[0].code_structure.class_name == "Patient"

    def test_mixed_languages(self):
        files = [
            _make_classified("java/com/acme/service/Billing.java"),
            _make_classified("cobol/BILLING.cbl"),
            _make_classified("sql/PKG_BILLING.pks"),
            _make_classified("docs/BRD.md"),
            _make_classified("src/test/java/BillingTest.java"),
        ]
        result = group_files(files)
        # Tier 1: java service + cobol service + stored_proc + doc = 4
        assert len(result.tier1_files) == 4
        # Tier 3: test = 1
        assert len(result.tier3_files) == 1

    def test_empty_input(self):
        result = group_files([])
        assert result.total_files == 0
        assert len(result.tier1_files) == 0
        assert len(result.tier2_groups) == 0

    def test_total_counts(self):
        files = [
            _make_classified("src/main/java/com/acme/service/A.java"),
            _make_classified("src/main/java/com/acme/entity/B.java"),
            _make_classified("src/main/java/com/acme/entity/C.java"),
            _make_classified("src/test/java/com/acme/DTest.java"),
            _make_classified("pom.xml"),
            _make_classified("docs/spec.md"),
        ]
        result = group_files(files)
        assert result.total_files == 6


class TestBuildGroupContent:
    def test_group_content_format(self):
        files = [_make_classified("src/main/java/com/acme/entity/Patient.java")]
        structures = {
            "Patient.java": CodeStructure(
                language="java",
                class_name="Patient",
                parent_class="BaseEntity",
                interfaces=["Serializable"],
                annotations=["Entity", "Table"],
                methods=[
                    MethodSignature(name="getName", return_type="String"),
                    MethodSignature(name="setName", params="String name"),
                ],
                sql_queries=["SELECT * FROM patients"],
                hardcoded_values=[],
                key_comments=["TODO: add validation"],
                dependencies=["BaseEntity"],
            ),
        }
        result = group_files(files, code_structures=structures)
        group = result.tier2_groups[0]
        content = build_group_content(group)

        assert "Package:" in content
        assert "Patient" in content
        assert "extends BaseEntity" in content
        assert "implements Serializable" in content
        assert "@Entity" in content
        assert "getName" in content
        assert "SELECT * FROM patients" in content
        assert "TODO: add validation" in content

    def test_tier3_summary_format(self):
        summary = {"test": 15, "dto": 8, "util": 5}
        filenames = [f"file{i}.java" for i in range(30)]
        content = build_tier3_summary(summary, filenames)

        assert "28 files" in content
        assert "test: 15" in content
        assert "dto: 8" in content
        assert "10 more" in content  # 30 files, shows 20, says "10 more"
