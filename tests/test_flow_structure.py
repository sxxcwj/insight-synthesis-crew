import sys
from pathlib import Path

src_path = str(Path(__file__).resolve().parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from craw.flow import AdvancedTwoStageFlow, ResearchFlowState


def test_flow_initialization_and_state():
    """验证 Flow 结构、初始状态与路由方法存在性"""
    flow = AdvancedTwoStageFlow()
    flow.state.topic = "AI Agent 测试主题"
    
    # 验证初始状态
    assert flow.state.topic == "AI Agent 测试主题"
    assert flow.state.retry_count == 0
    assert flow.state.phase1_passed is False
    assert flow.state.final_report is None

    # 验证关键阶段监听器与路由已定义
    assert hasattr(flow, "initialize")
    assert hasattr(flow, "run_scout_phase")
    assert hasattr(flow, "quality_gate")
    assert hasattr(flow, "run_analyst_phase")
    assert hasattr(flow, "save_and_export_report")

    print("🎉 AdvancedTwoStageFlow 状态模型与路由结构全部通过验证！")


if __name__ == "__main__":
    test_flow_initialization_and_state()
