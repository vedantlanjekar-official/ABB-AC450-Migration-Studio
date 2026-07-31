import pytest
import time
from pathlib import Path
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_api_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "online"

def test_full_api_conversion_flow_multi_block_defaults():
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "examples" / "sample_ac450_db.pdf"
    assert sample_pdf.exists()

    # 1. Upload
    with open(sample_pdf, "rb") as f:
        response = client.post("/api/upload", files={"files": ("sample_ac450_db.pdf", f, "application/pdf")})
    
    assert response.status_code == 200
    upload_data = response.json()
    job_id = upload_data["job_id"]
    assert job_id is not None
    assert upload_data["total_files"] == 1

    # 2. Trigger Process
    proc_res = client.post("/api/process", json={"job_id": job_id, "conversion_type": "DB"})
    assert proc_res.status_code == 200

    # 3. Poll Status until completed
    max_retries = 15
    completed = False
    for _ in range(max_retries):
        status_res = client.get(f"/api/status/{job_id}")
        assert status_res.status_code == 200
        st = status_res.json()
        if st["status"] == "completed":
            completed = True
            assert st["total_objects"] >= 4
            assert st["merged_profiles_created"] >= 2
            assert st["parameters_filled_from_defaults"] > 0
            assert st["ignored_header_footer_lines"] > 0
            assert "Clubbed_IO" in st["generated_sheets"]
            break
        time.sleep(0.3)

    assert completed, "API conversion did not complete within timeout"

    # 4. Download Excel — filename matches uploaded PDF basename
    dl_res = client.get(f"/api/download/{job_id}")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(dl_res.content) > 1000
    cd = dl_res.headers.get("content-disposition", "")
    assert "sample_ac450_db.xlsx" in cd

    # 5. Get Logs
    log_res = client.get(f"/api/logs/{job_id}")
    assert log_res.status_code == 200
    assert "HIERARCHICAL AST COMPILER ENGINE AUDIT REPORT" in log_res.text

def test_full_api_conversion_flow_pc_element():
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "examples" / "sample_ac450_db.pdf"
    assert sample_pdf.exists()

    # 1. Upload
    with open(sample_pdf, "rb") as f:
        response = client.post("/api/upload", files={"files": ("pc_sample.pdf", f, "application/pdf")})

    assert response.status_code == 200
    job_id = response.json()["job_id"]

    # 2. Trigger PC Process
    proc_res = client.post("/api/process", json={"job_id": job_id, "conversion_type": "PC"})
    assert proc_res.status_code == 200
    assert proc_res.json()["conversion_type"] == "PC"

    # 3. Poll Status
    max_retries = 15
    completed = False
    for _ in range(max_retries):
        status_res = client.get(f"/api/status/{job_id}")
        assert status_res.status_code == 200
        st = status_res.json()
        if st["status"] == "completed":
            completed = True
            assert st["conversion_type"] == "PC"
            assert ("Valmet PC Export" in st["generated_sheets"] or "I_O_List" in st["generated_sheets"])
            break
        time.sleep(0.3)

    assert completed, "PC API conversion did not complete within timeout"

    # 4. Download PC Excel — filename matches uploaded PDF basename
    dl_res = client.get(f"/api/download/{job_id}")
    assert dl_res.status_code == 200
    assert len(dl_res.content) > 500
    cd = dl_res.headers.get("content-disposition", "")
    assert "pc_sample.xlsx" in cd

def test_multi_file_unified_default_inheritance():
    sample_pdf = Path(__file__).resolve().parent.parent.parent / "examples" / "sample_ac450_db.pdf"
    assert sample_pdf.exists()

    # Upload 2 copies of the sample PDF in a single job (simulating multi-file upload)
    with open(sample_pdf, "rb") as f1, open(sample_pdf, "rb") as f2:
        response = client.post(
            "/api/upload",
            files=[
                ("files", ("part1.pdf", f1, "application/pdf")),
                ("files", ("part2.pdf", f2, "application/pdf"))
            ]
        )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert response.json()["total_files"] == 2

    # Trigger conversion process
    proc_res = client.post("/api/process", json={"job_id": job_id, "conversion_type": "DB"})
    assert proc_res.status_code == 200

    # Poll status until completed
    max_retries = 20
    completed = False
    for _ in range(max_retries):
        status_res = client.get(f"/api/status/{job_id}")
        assert status_res.status_code == 200
        st = status_res.json()
        if st["status"] == "completed":
            completed = True
            # Multi-file combination MUST combine elements across both files cleanly
            assert st["total_objects"] >= 8
            break
        time.sleep(0.3)

    assert completed, "Multi-file conversion did not complete within timeout"
