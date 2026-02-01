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

router = APIRouter()

# Configuration
UPLOAD_FOLDER = Path("uploads")
UPLOAD_FOLDER.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".txt"}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB


def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File()],
    db: Session = Depends(get_db)
):
    """
    Upload and parse a conversation file.
    
    Returns parsed profile, cash flows, and adviser config.
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    if not allowed_file(file.filename):
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a .txt file."
        )
    
    # Save uploaded file
    filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    filepath = UPLOAD_FOLDER / filename
    
    try:
        # Read and save file
        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large (max 16MB)")
        
        filepath.write_bytes(contents)
        
        # TODO: Replace user_id=1 with actual authenticated user
        parser = ParserService(user_id=get_current_active_user().id, filepath=str(filepath), db=db)
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

