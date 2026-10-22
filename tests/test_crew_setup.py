import sys
from pathlib import Path

src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from craw.crew import TwoStageResearchCrew
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, FileReadTool


def test_crew_structure_and_tool_restrictions():
    """验证 Agent、Task、工具限制与上下文流向配置"""
    research_crew = TwoStageResearchCrew()
    crew = research_crew.crew()

    # 1. 验证 Agent 数量与角色
    assert len(crew.agents) == 2, f"预期 2 个 Agent，实际有 {len(crew.agents)} 个"
    scout = crew.agents[0]
    analyst = crew.agents[1]

    print(f"✅ Scout Role: {scout.role}")
    print(f"✅ Analyst Role: {analyst.role}")

    # 2. 验证工具限制 (Least Privilege)
    scout_tool_classes = [t.__class__.__name__ for t in scout.tools]
    analyst_tool_classes = [t.__class__.__name__ for t in analyst.tools]

    print(f"🔧 Scout Tools: {scout_tool_classes}")
    print(f"🔧 Analyst Tools: {analyst_tool_classes}")

    # Analyst 必须没有 SerperDevTool 或 ScrapeWebsiteTool
    assert "SerperDevTool" not in analyst_tool_classes, "Analyst 绝不能拥有搜索工具！"
    assert "ScrapeWebsiteTool" not in analyst_tool_classes, "Analyst 绝不能拥有抓取工具！"
    assert any("FileRead" in name for name in analyst_tool_classes), "Analyst 必须具备本地文件读取工具"

    # 3. 验证调用频次限制
    assert scout.max_iter <= 8, f"Scout max_iter 应 <= 8, 实际为 {scout.max_iter}"
    assert analyst.max_iter <= 5, f"Analyst max_iter 应 <= 5, 实际为 {analyst.max_iter}"
    assert scout.allow_delegation is False, "Scout 应禁止递归 delegation"
    assert analyst.allow_delegation is False, "Analyst 应禁止递归 delegation"

    # 4. 验证 Task 依赖与上下文传递
    assert len(crew.tasks) == 2, f"预期 2 个 Task，实际为 {len(crew.tasks)}"
    phase1_task = crew.tasks[0]
    phase2_task = crew.tasks[1]

    assert phase2_task.context is not None and len(phase2_task.context) > 0, "Phase 2 Task 必须依赖 Phase 1 Task 的上下文"
    assert phase2_task.context[0] == phase1_task, "Phase 2 的直接前置依赖应为 Phase 1 Task"

    print("\n🎉 所有两阶段研究员架构与工具安全约束验证通过！")


if __name__ == "__main__":
    test_crew_structure_and_tool_restrictions()
