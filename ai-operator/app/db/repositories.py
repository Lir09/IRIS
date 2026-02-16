from sqlalchemy.orm import Session
from app.db.database import ApprovalORM, RunORM
from app.models.schemas import Approval, Run, ApprovalStatus

class ApprovalRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_approval(self, approval: Approval) -> ApprovalORM:
        db_approval = ApprovalORM(**approval.dict())
        self.db.add(db_approval)
        self.db.commit()
        self.db.refresh(db_approval)
        return db_approval

    def get_approval(self, approval_id: str) -> ApprovalORM | None:
        return self.db.query(ApprovalORM).filter(ApprovalORM.id == approval_id).first()

    def update_approval_status(self, approval_id: str, status: ApprovalStatus) -> ApprovalORM | None:
        db_approval = self.get_approval(approval_id)
        if db_approval:
            db_approval.status = status.value
            self.db.commit()
            self.db.refresh(db_approval)
        return db_approval

class RunRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_run(self, run: Run) -> RunORM:
        db_run = RunORM(**run.dict())
        self.db.add(db_run)
        self.db.commit()
        self.db.refresh(db_run)
        return db_run

    def get_run(self, run_id: str) -> RunORM | None:
        return self.db.query(RunORM).filter(RunORM.id == run_id).first()
