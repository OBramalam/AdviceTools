import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services import ParserService
from schemas.base_schemas import AdviserConfig
from api.schemas.responses import UploadResponse
from api.dependencies import get_db, get_current_active_user
from infra.database.models.user import User

router = APIRouter()

# Configuration
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
# Formats supported by LlamaParse for document extraction
ALLOWED_EXTENSIONS = {
    ".txt", ".pdf", ".doc", ".docx", ".docm", ".rtf", ".html", ".htm", ".xml", ".epub",
    ".csv", ".tsv", ".xlsx", ".xls", ".xlsm", ".xlsb", ".ods",
    ".ppt", ".pptx", ".pptm",
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".svg",
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Upload and parse a document (conversation transcript, financial statement, etc.).

    Supports PDF, DOC/DOCX, TXT, CSV, XLSX, images, and other formats supported by LlamaParse.
    Returns parsed financial plan, cash flows, and adviser config.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type. Accepted: PDF, DOC/DOCX, TXT, CSV, XLSX, PNG, JPG, and other common document formats."
        )

    suffix = Path(file.filename).suffix.lower()
    if not suffix:
        suffix = ".txt"
    # Save uploaded file with original extension (required for parser)
    filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}"
    filepath = UPLOAD_FOLDER / filename
    
    try:
        # Read and save file
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 25MB)")
        
        filepath.write_bytes(contents)

        parser = ParserService(user_id=current_user.id, filepath=str(filepath), db=db)
        financial_plan, cash_flows, portfolios = parser.extract_data()
        
        adviser_config = AdviserConfig()
        
        return UploadResponse(
            success=True,
            financial_plan=financial_plan,
            cash_flows=cash_flows,
            adviser_config=adviser_config
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error parsing conversation: {str(e)}"
        )

