import sys
from pathlib import Path

# 将 src 目录加入模块搜索路径
src_path = str(Path(__file__).resolve().parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from craw.crew import TwoStageResearchCrew
from craw.flow import AdvancedTwoStageFlow


def run():
    """执行两阶段协同研究：支持标准 Crew 模式与自愈 Flow 模式"""
    args = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    use_flow = "--flow" in sys.argv
    do_plot = "--plot" in sys.argv

    topic = (
        args[0]
        if args
        else "2025-2026年自主智能体（AI Agents）在企业级软件系统中的落地瓶颈与演进趋势"
    )

    if do_plot:
        print("📊 正在生成 Flow 工作流结构图 (flow_plot.html)...")
        flow = AdvancedTwoStageFlow()
        flow.plot("flow_plot")
        print("✅ 结构图已生成！可在浏览器中打开 flow_plot.html 查看。")
        return

    if use_flow:
        print("=" * 60)
        print(f"🔄 启动【自愈 Flow 模式】两阶段工作流: {topic}")
        print("=" * 60)
        flow = AdvancedTwoStageFlow()
        flow.state.topic = topic
        flow.kickoff()
        print("\n" + "=" * 60)
        print("🏁 Flow 执行完成，最终产物已导出。")
        print("=" * 60)
    else:
        print("=" * 60)
        print(f"🎯 启动【标准 Crew 模式】两阶段研究流程: {topic}")
        print("=" * 60)
        crew_instance = TwoStageResearchCrew().crew()
        result = crew_instance.kickoff(inputs={"topic": topic})

        print("\n" + "=" * 60)
        print("📋 研究交付结果 (Raw Markdown & Pydantic)")
        print("=" * 60)
        print(result.raw)

        # 自动归档并导出 Word（支持时间戳历史归档与最新镜像）
        import shutil
        from craw.export_docx import get_report_paths, export_markdown_to_docx

        output_dir = Path("reports")
        archive_md, archive_docx, latest_md, latest_docx = get_report_paths(
            output_dir, topic
        )

        with open(archive_md, "w", encoding="utf-8") as f:
            f.write(f"# 研究课题：{topic}\n\n{result.raw}")

        try:
            export_markdown_to_docx(archive_md, archive_docx)
            shutil.copy2(archive_md, latest_md)
            shutil.copy2(archive_docx, latest_docx)
            print(f"\n💾 [历史永久归档] Markdown 已保存至: {archive_md}")
            print(f"📄 [历史永久归档] Word 文档已保存至: {archive_docx}")
            print(f"⭐ [最新便捷镜像] 已同步镜像至: {latest_docx}")
        except Exception as e:
            print(f"Word 文档处理提示: {e}")



if __name__ == "__main__":
    run()
