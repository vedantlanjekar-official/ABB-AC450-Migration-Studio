from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.services.job_manager import job_store

router = APIRouter(prefix="/download", tags=["Download"])


@router.get("/{job_id}")
async def download_excel_export(job_id: str):
    """
    Downloads generated Valmet-compatible Excel workbook for a completed job.

    Download filename matches the on-disk export name (PDF basename → .xlsx for
    DB/PC conversions; fixed report names for standalone Excel workflows).
    """
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job ID {job_id} not found.")

    if job["status"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job {job_id} is not completed yet. Current status: {job['status']}",
        )

    excel_path_str = job.get("excel_file_path")
    if not excel_path_str or not Path(excel_path_str).exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "Generated Excel export file not found. "
                "The server may have restarted after conversion — please run the conversion again."
            ),
        )

    excel_path = Path(excel_path_str)
    conversion_type = (job.get("conversion_type") or "DB").upper()
    if conversion_type in {"COMPARE", "EXCEL", "EXCEL_COMPARE"}:
        export_filename = "Comparison_Report.xlsx"
    elif conversion_type in {"IO_ARRANGE", "IO_ADDRESS", "ARRANGE"}:
        export_filename = "IO_Address_Arrangement.xlsx"
    elif conversion_type in {
        "ENG_TEMPLATE",
        "ENGINEERING_TEMPLATE",
        "ABB_TEMPLATE",
        "TEMPLATE",
    }:
        export_filename = "ABB_Engineering_Template.xlsx"
    else:
        # Prefer the real export basename (e.g. Plant_Area_01.xlsx)
        export_filename = excel_path.name or "export.xlsx"

    return FileResponse(
        path=str(excel_path),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=export_filename,
    )
