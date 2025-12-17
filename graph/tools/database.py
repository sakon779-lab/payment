from langchain_core.tools import tool
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.knowledge import JiraKnowledge
from datetime import datetime


@tool
def save_ticket_knowledge(
        issue_key: str,
        summary: str,
        issue_type: str = "Task",
        parent_key: str = None,
        business_logic: str = None,
        technical_spec: str = None,
        test_scenarios: str = None,
        status: str = "UNKNOWN"
) -> str:
    """
    Saves or updates summarized Jira ticket knowledge into the database.
    Use this tool AFTER you have analyzed and categorized the ticket content.

    Args:
        issue_key: The Jira ticket ID (e.g., PAY-001)
        summary: Brief title of the ticket
        issue_type: Type of issue (Epic, Story, Task, Bug)
        parent_key: ID of the parent ticket (if any)
        business_logic: Summarized business rules, flows, and requirements
        technical_spec: Summarized technical details (API, DB, Libs)
        test_scenarios: Summarized test cases and acceptance criteria
        status: Current status of the ticket
    """

    session: Session = SessionLocal()
    try:
        # ใช้ merge เพื่อทำ Upsert (ถ้ามีอยู่แล้วจะแก้ ถ้าไม่มีจะสร้างใหม่)
        knowledge = JiraKnowledge(
            issue_key=issue_key,
            issue_type=issue_type,
            parent_key=parent_key,
            summary=summary,
            business_logic=business_logic,
            technical_spec=technical_spec,
            test_scenarios=test_scenarios,
            status=status,
            last_synced_at=datetime.now()
        )

        session.merge(knowledge)
        session.commit()
        return f"✅ Successfully saved knowledge for {issue_key}."

    except Exception as e:
        session.rollback()
        return f"❌ Error saving to DB: {str(e)}"
    finally:
        session.close()