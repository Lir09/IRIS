import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.repositories import ApprovalRepository, RunRepository
from app.models.schemas import ExecutionResponse, ApprovalStatus, Run
from app.tools.powershell_tool import PowerShellTool

router = APIRouter()
logger = logging.getLogger(__name__)
powershell_tool = PowerShellTool()

@router.post("/approvals/{approval_id}/execute", tags=["Approvals"], response_model=ExecutionResponse)
def execute_approved_task(approval_id: str, db: Session = Depends(get_db)):
    """
    Executes a task that has been approved.
    """
    approval_repo = ApprovalRepository(db)
    run_repo = RunRepository(db)

    approval = approval_repo.get_approval(approval_id)

    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval ID not found.")
    
    if approval.status != ApprovalStatus.PENDING.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This approval request has already been processed with status: '{approval.status}'.",
        )

    # Execute the command
    logger.info(f"Executing approved command for approval_id '{approval_id}': '{approval.proposed_command}'")
    execution_result = powershell_tool.execute(
        command=approval.proposed_command,
        cwd=approval.cwd
    )

    # Create run log
    run_log = Run(
        approval_id=approval.id,
        command=approval.proposed_command,
        cwd=approval.cwd,
        **execution_result, # Puts returncode, stdout, stderr, ok
    )
    db_run = run_repo.create_run(run_log)
    logger.info(f"Created run log with id '{db_run.id}'")

    # Update approval status
    approval_repo.update_approval_status(approval_id, ApprovalStatus.EXECUTED)
    logger.info(f"Updated approval '{approval_id}' to status '{ApprovalStatus.EXECUTED.value}'")


    return ExecutionResponse(run_id=db_run.id, **execution_result)
