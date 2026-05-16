"""Tests for code structure extraction skill."""

from src.agents.ingest.skills.code_structure_skill import (
    CodeStructure,
    extract_code_structure,
)


class TestJavaExtractor:
    def test_package_and_class(self):
        code = """
package com.acme.billing.service;

import com.acme.billing.model.Invoice;
import com.acme.billing.repository.InvoiceRepository;

@Service
@Transactional
public class InvoiceService extends BaseService implements Billable {

    private final InvoiceRepository invoiceRepo;
    private final PaymentGateway gateway;

    public BigDecimal calculateTotal(Invoice invoice) {
        return invoice.getAmount().add(invoice.getTax());
    }

    @Transactional
    public void processPayment(Invoice invoice, String paymentMethod) {
        if (invoice.getAmount() > 5000) {
            // TODO: implement approval workflow
        }
    }
}
"""
        cs = extract_code_structure(code, "com/acme/billing/service/InvoiceService.java", "java")
        assert cs.package == "com.acme.billing.service"
        assert cs.class_name == "InvoiceService"
        assert cs.parent_class == "BaseService"
        assert "Billable" in cs.interfaces
        assert len(cs.methods) >= 2
        method_names = [m.name for m in cs.methods]
        assert "calculateTotal" in method_names
        assert "processPayment" in method_names
        assert "InvoiceRepository" in cs.dependencies
        assert any("TODO" in c for c in cs.key_comments)

    def test_spring_rest_controller(self):
        code = """
package com.acme.api;

@RestController
@RequestMapping("/api/patients")
public class PatientController {

    @GetMapping("/{id}")
    public Patient getPatient(@PathVariable Long id) {
        return patientService.findById(id);
    }

    @PostMapping("/")
    public Patient createPatient(@RequestBody PatientDTO dto) {
        return patientService.create(dto);
    }
}
"""
        cs = extract_code_structure(code, "PatientController.java", "java")
        assert cs.class_name == "PatientController"
        assert len(cs.entry_points) >= 1  # picks up @RequestMapping/@GetMapping endpoints

    def test_embedded_sql(self):
        code = '''
public class PatientDAO {
    public List<Patient> search(String term) {
        String sql = "SELECT * FROM patients WHERE name LIKE '%" + term + "%'";
        return jdbcTemplate.query(sql, mapper);
    }
}
'''
        cs = extract_code_structure(code, "PatientDAO.java", "java")
        assert len(cs.sql_queries) >= 1

    def test_ejb_detection(self):
        code = """
@Stateless
public class BillingBean {
    @Resource
    private DataSource ds;
}
"""
        cs = extract_code_structure(code, "BillingBean.java", "java")
        assert "EJB" in cs.annotations

    def test_hardcoded_values(self):
        code = """
public class Config {
    private static final int THRESHOLD = 10000;
    private static final String API_KEY = "sk-1234567890abcdef";
}
"""
        cs = extract_code_structure(code, "Config.java", "java")
        assert any(hv.name == "THRESHOLD" for hv in cs.hardcoded_values)


class TestCobolExtractor:
    def test_program_id_and_paragraphs(self):
        code = """
       IDENTIFICATION DIVISION.
       PROGRAM-ID. BILLING-CALC.

       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-TOTAL         PIC 9(7)V99.
       01 WS-STATUS.
          88 VALID-STATUS   VALUE 'A' 'B' 'C'.
          88 INVALID-STATUS VALUE 'X' 'Z'.

       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM CALCULATE-TOTAL.
           PERFORM WRITE-OUTPUT.
           STOP RUN.

       CALCULATE-TOTAL.
           EXEC SQL
               SELECT SUM(amount) INTO :WS-TOTAL
               FROM billing_claims
               WHERE status = 'PENDING'
           END-EXEC.

       WRITE-OUTPUT.
           CALL 'PRINTPGM' USING WS-TOTAL.

"""
        cs = extract_code_structure(code, "BILLING-CALC.cbl", "cobol")
        assert cs.class_name == "BILLING-CALC"
        assert any(m.name == "MAIN-LOGIC" for m in cs.methods)
        assert any(m.name == "CALCULATE-TOTAL" for m in cs.methods)
        assert len(cs.sql_queries) >= 1
        assert "SELECT" in cs.sql_queries[0]
        assert "PRINTPGM" in cs.dependencies
        assert any("VALID-STATUS" in c for c in cs.key_comments)

    def test_cics_commands(self):
        code = """
       PROCEDURE DIVISION.
       MAIN-PARA.
           EXEC CICS RECEIVE
               INTO(WS-INPUT)
               LENGTH(WS-LEN)
           END-EXEC.
           EXEC CICS SEND
               FROM(WS-OUTPUT)
           END-EXEC.
"""
        cs = extract_code_structure(code, "ONLINE.cbl", "cobol")
        assert any("CICS RECEIVE" in ep for ep in cs.entry_points)
        assert any("CICS SEND" in ep for ep in cs.entry_points)

    def test_copybook_references(self):
        code = """
       DATA DIVISION.
       WORKING-STORAGE SECTION.
           COPY CUSTCPY.
           COPY ADDRCPY.
"""
        cs = extract_code_structure(code, "MAIN.cbl", "cobol")
        assert "CUSTCPY" in cs.imports
        assert "ADDRCPY" in cs.imports


class TestPlsqlExtractor:
    def test_package_with_procedures(self):
        code = """
CREATE OR REPLACE PACKAGE BODY PKG_BILLING AS

    PROCEDURE process_claim(p_claim_id IN NUMBER, p_status OUT VARCHAR2) IS
        CURSOR c_items IS
            SELECT item_id, amount FROM claim_items WHERE claim_id = p_claim_id;
    BEGIN
        FOR rec IN c_items LOOP
            -- process each item
            NULL;
        END LOOP;
    EXCEPTION
        WHEN NO_DATA_FOUND THEN
            p_status := 'NOT_FOUND';
        WHEN OTHERS THEN
            DBMS_OUTPUT.PUT_LINE('Error: ' || SQLERRM);
    END;

    FUNCTION calc_total(p_claim_id IN NUMBER) RETURN NUMBER IS
        v_total billing_claims.amount%TYPE;
    BEGIN
        SELECT SUM(amount) INTO v_total FROM claim_items WHERE claim_id = p_claim_id;
        RETURN v_total;
    END;

END PKG_BILLING;
"""
        cs = extract_code_structure(code, "PKG_BILLING.pkb", "plsql")
        assert cs.class_name == "PKG_BILLING"
        assert any(m.name == "process_claim" for m in cs.methods)
        assert any(m.name == "calc_total" for m in cs.methods)
        assert any("CURSOR" in sq for sq in cs.sql_queries)
        assert "DBMS_OUTPUT" in cs.dependencies
        assert any("NO_DATA_FOUND" in kc for kc in cs.key_comments)
        # %TYPE reference
        assert any("billing_claims" in d for d in cs.dependencies)

    def test_trigger(self):
        code = """
CREATE OR REPLACE TRIGGER TRG_AUDIT_PATIENT
    AFTER INSERT OR UPDATE ON patients
    FOR EACH ROW
BEGIN
    INSERT INTO audit_log VALUES (SYSDATE, :NEW.patient_id, 'MODIFIED');
END;
"""
        cs = extract_code_structure(code, "TRG_AUDIT.trg", "plsql")
        assert any("TRIGGER: TRG_AUDIT_PATIENT" in ep for ep in cs.entry_points)


class TestProgress4glExtractor:
    def test_procedures_and_queries(self):
        code = """
PROCEDURE calculate-invoice:
    DEFINE INPUT PARAMETER p-inv-id AS INTEGER NO-UNDO.
    DEFINE OUTPUT PARAMETER p-total AS DECIMAL NO-UNDO.

    FOR EACH invoice-line WHERE invoice-line.inv-id = p-inv-id:
        p-total = p-total + invoice-line.amount.
    END.
END PROCEDURE.

FUNCTION get-discount RETURNS DECIMAL (p-customer AS CHARACTER):
    FIND FIRST customer WHERE customer.name = p-customer NO-ERROR.
    RETURN customer.discount-pct.
END FUNCTION.

RUN print-invoice.p (INPUT p-inv-id).
"""
        cs = extract_code_structure(code, "inv-calc.p", "progress_4gl")
        assert any(m.name == "calculate-invoice" for m in cs.methods)
        assert any(m.name == "get-discount" and m.return_type == "DECIMAL" for m in cs.methods)
        assert any("FOR EACH" in sq for sq in cs.sql_queries)
        assert any("FIND" in sq for sq in cs.sql_queries)
        assert "print-invoice.p" in cs.dependencies

    def test_temp_table_and_includes(self):
        code = """
{common/std-vars.i}
{common/error-handler.i}

DEFINE TEMP-TABLE tt-result
    FIELD cust-id AS INTEGER
    FIELD cust-name AS CHARACTER.
"""
        cs = extract_code_structure(code, "report.p", "progress_4gl")
        assert "common/std-vars.i" in cs.imports
        assert any("TEMP-TABLE: tt-result" in kc for kc in cs.key_comments)


class TestVb6Extractor:
    def test_subs_and_functions(self):
        code = """
Public Sub ProcessBilling(patientId As Long)
    Dim conn As New ADODB.Connection
    conn.Open "Provider=SQLOLEDB;..."
    Dim sql As String
    sql = "SELECT * FROM billing WHERE patient_id = " & patientId
    conn.Execute sql
End Sub

Private Function CalcTotal(amount As Double, tax As Double) As Double
    CalcTotal = amount + tax
End Function
"""
        cs = extract_code_structure(code, "BillingModule.bas", "vb6")
        assert any(m.name == "ProcessBilling" for m in cs.methods)
        assert any(m.name == "CalcTotal" and m.return_type == "Double" for m in cs.methods)
        assert "ADODB" in cs.dependencies
        assert len(cs.sql_queries) >= 1


class TestPythonExtractor:
    def test_class_and_methods(self):
        code = """
from src.services.billing import BillingService
import os

APPROVAL_THRESHOLD = 5000

class PatientService(BaseService):
    # TODO: add caching

    def search(self, term: str) -> list[Patient]:
        sql = f"SELECT * FROM patients WHERE name LIKE '%{term}%'"
        return self.db.execute(sql)

    @staticmethod
    def validate(patient: Patient) -> bool:
        return patient.name is not None
"""
        cs = extract_code_structure(code, "patient_service.py", "python")
        assert cs.class_name == "PatientService"
        assert cs.parent_class == "BaseService"
        assert any(m.name == "search" for m in cs.methods)
        assert any(m.name == "validate" for m in cs.methods)
        assert len(cs.sql_queries) >= 1
        assert any("TODO" in c for c in cs.key_comments)
        assert any(hv.name == "APPROVAL_THRESHOLD" for hv in cs.hardcoded_values)


class TestSqlExtractor:
    def test_tables_and_triggers(self):
        code = """
CREATE TABLE patients (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    ssn VARCHAR(11)
);

CREATE TABLE appointments (
    id SERIAL PRIMARY KEY,
    patient_id INT REFERENCES patients(id)
);

CREATE OR REPLACE TRIGGER trg_audit
    AFTER INSERT ON patients
    FOR EACH ROW EXECUTE FUNCTION audit_fn();

CREATE INDEX idx_patient_name ON patients(name);
-- IMPORTANT: SSN should be encrypted
"""
        cs = extract_code_structure(code, "schema.sql", "sql")
        assert any("TABLE: patients" in m.name for m in cs.methods)
        assert any("TABLE: appointments" in m.name for m in cs.methods)
        assert any("TRIGGER: trg_audit" in ep for ep in cs.entry_points)
        assert any("INDEX: idx_patient_name" in kc for kc in cs.key_comments)
        assert any("IMPORTANT" in kc for kc in cs.key_comments)


class TestGenericExtractor:
    def test_unknown_language(self):
        code = "SELECT name FROM table1; -- TODO: fix this"
        cs = extract_code_structure(code, "unknown.xyz", "unknown")
        assert cs.language == "unknown"
        assert len(cs.sql_queries) >= 1
        assert any("TODO" in c for c in cs.key_comments)

    def test_empty_content(self):
        cs = extract_code_structure("", "empty.java", "java")
        assert cs.language == "java"
        assert cs.class_name == ""
