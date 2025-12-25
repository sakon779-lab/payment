# batch_run.py

import os
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from graph.workflow import build_graph
from graph.tools.jira import search_jira_issues  # import tool ที่เพิ่งสร้าง

# โหลด Environment
load_dotenv()


def run_batch_sync():
    print("🚀 STARTING BATCH SYNC PROCESS...")

    # 1. ค้นหา Ticket ทั้งหมดมาก่อน (เรียก Tool โดยตรงแบบ Python Function)
    # คุณสามารถแก้ JQL ตรงนี้ได้ เช่น "project = SCRUM AND status != Done"
    print("🔍 Scanning Jira Board...")
    search_result = search_jira_issues.invoke({"jql_query": "project = SCRUM ORDER BY created DESC"})

    if "Error" in search_result or "No issues found" in search_result:
        print(f"❌ Aborted: {search_result}")
        return

    # แกะ List ออกมาจาก String (วิธีบ้านๆ แต่ชัวร์)
    # format: "Found X issues: A, B, C"
    issue_keys_str = search_result.split(": ")[1]
    ticket_list = [k.strip() for k in issue_keys_str.split(",")]

    print(f"✅ Target Locked: {len(ticket_list)} tickets found.")
    print(f"📋 List: {ticket_list}\n")

    # 2. สร้าง AI Agent (Graph)
    app = build_graph()

    # 3. วนลูปส่งงานทีละใบ
    for i, ticket_key in enumerate(ticket_list):
        print("=" * 40)
        print(f"🤖 PROCESSING [{i + 1}/{len(ticket_list)}]: {ticket_key}")
        print("=" * 40)

        try:
            # เรียก Agent ให้ทำงานกับ Ticket นี้
            app.invoke(
                {"messages": [HumanMessage(content=f"Sync data for {ticket_key}")]},
                config={"recursion_limit": 20}
            )
            print(f"✅ Finished {ticket_key}\n")

        except Exception as e:
            print(f"❌ Failed to sync {ticket_key}: {e}\n")

    print("🎉 ALL DONE! BATCH SYNC COMPLETED.")


if __name__ == "__main__":
    run_batch_sync()