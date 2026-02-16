from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.repositories import RunRepository
from app.models.schemas import Run

router = APIRouter()

@router.get("/runs/{run_id}", tags=["Runs"], response_model=Run)
def get_run_log(run_id: str, db: Session = Depends(get_db)):
    """
    Retrieves the execution log for a specific run.
    """
    run_repo = RunRepository(db)
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run ID not found.")
    return run
