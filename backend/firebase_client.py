import os
import base64
import firebase_admin
from firebase_admin import credentials, firestore, db as rtdb
from datetime import datetime, timezone

_app = None


def _init():
    global _app
    if _app is None:
        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "./firebase-service-account.json")
        cred = credentials.Certificate(cred_path)
        _app = firebase_admin.initialize_app(cred, {
            "databaseURL": os.environ.get("FIREBASE_DATABASE_URL"),
        })


def get_db():
    _init()
    return firestore.client()


def update_submission(submission_id: str, data: dict):
    _init()
    get_db().collection("submissions").document(submission_id).update({
        **data,
        "updatedAt": datetime.now(timezone.utc),
    })
    # Mirror status to Realtime Database for real-time frontend listeners
    if "status" in data:
        rtdb.reference(f"submission_status/{submission_id}").set({
            "status": data["status"],
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        })


def write_ai_result(submission_id: str, result: dict):
    _init()
    # Remove non-serialisable keys before writing to Firestore
    clean = {k: v for k, v in result.items() if k != "extracted_data"}
    get_db().collection("ai_results").document(submission_id).set({
        **clean,
        "processedAt": datetime.now(timezone.utc),
    })


def get_submission(submission_id: str) -> dict | None:
    _init()
    doc = get_db().collection("submissions").document(submission_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None


def save_certificate(submission_id: str, pdf_bytes: bytes):
    """Store approval certificate PDF as base64 in Realtime Database."""
    _init()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    rtdb.reference(f"certificates/{submission_id}").set({
        "pdf_base64": pdf_b64,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def save_report(submission_id: str, pdf_bytes: bytes):
    """Store rejection report PDF as base64 in Realtime Database."""
    _init()
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    rtdb.reference(f"reports/{submission_id}").set({
        "pdf_base64": pdf_b64,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
