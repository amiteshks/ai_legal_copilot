# This file defines an API endpoint for extracting legal information from uploaded PDF files.
from fastapi import APIRouter, UploadFile
from app.services.pipeline import pdf_processor_workflow

router = APIRouter()

# End point to extract legal info from uploaded PDF
@router.post("/extract")
async def extract_legal_info(file: UploadFile):
    output = await pdf_processor_workflow(file)
    print(f"extract_legal_info Results: {output}")
    return {
        "status": "ok",
        "summary": output.get("summary"),
        "results": output.get("results", []),
        "triggers": output.get("triggers", {})
    }
