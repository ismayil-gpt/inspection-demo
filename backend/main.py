import os
import time
import traceback
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import base64

from analyser import analyse_blueprint
from certificate_generator import generate_approval_certificate, generate_rejection_report

app = FastAPI(title="CivGuard AI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyse")
async def analyse(
    submission_id: str = Form(...),
    form_data: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Analyse a blueprint and return the full result + generated PDF as base64.
    No Firebase Admin SDK required — frontend writes results back to Firebase.
    """
    start = time.time()
    file_bytes = await file.read()
    file_type = file.content_type or "application/pdf"

    try:
        parsed_form = json.loads(form_data)
    except Exception:
        parsed_form = {}

    try:
        result = analyse_blueprint(file_bytes, file_type, parsed_form)
        result["processing_time_s"] = round(time.time() - start, 2)

        # Generate PDF certificate/report and include as base64 in response
        if result["overall_result"] == "approved":
            pdf_bytes = generate_approval_certificate(submission_id, parsed_form, result)
            result["certificate_pdf_base64"] = base64.b64encode(pdf_bytes).decode("utf-8")
        else:
            pdf_bytes = generate_rejection_report(submission_id, parsed_form, result)
            result["report_pdf_base64"] = base64.b64encode(pdf_bytes).decode("utf-8")

        return JSONResponse(content={"success": True, "result": result})

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
