from sqlalchemy import Column, String, Text, DateTime, func
from app.db.base_class import Base  # ตรวจสอบว่าใน project คุณใช้ Base จากไหน (ปกติคือ app.db.base)


class JiraKnowledge(Base):
    __tablename__ = "jira_knowledge"

    # --- Identity & Hierarchy ---
    issue_key = Column(String, primary_key=True, index=True, comment="Jira Issue Key (e.g. PAY-001)")
    issue_type = Column(String, nullable=False, index=True, comment="Type: Epic, Story, Task, Bug")
    parent_key = Column(String, nullable=True, index=True, comment="Parent Issue Key (e.g. PAY-001)")

    # --- Content ---
    summary = Column(String, nullable=False)

    # Structured Knowledge (AI Generated)
    business_logic = Column(Text, nullable=True, comment="Summarized Business Rules & Logic")
    technical_spec = Column(Text, nullable=True, comment="Technical constraints, API, DB details")
    test_scenarios = Column(Text, nullable=True, comment="Test cases and acceptance criteria")

    # --- Metadata ---
    status = Column(String, default="UNKNOWN")
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Raw Data (Optional backup)
    raw_description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<JiraKnowledge(key={self.issue_key}, type={self.issue_type}, summary={self.summary})>"