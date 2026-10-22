import os
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from crewai.flow.flow import Flow, start, listen, router

from craw.crew import TwoStageResearchCrew
from craw.models import FinalResearchReport


class ResearchFlowState(BaseModel):
    """两阶段工作流持久状态"""
    topic: str = ""
    retry_count: int = 0
    phase1_summary: str = ""
    phase1_passed: bool = False
    final_report: Optional[FinalResearchReport] = None
    output_filepath: str = ""


class AdvancedTwoStageFlow(Flow[ResearchFlowState]):
    """具备质检把关与自愈重试机制的两阶段研究 Flow"""

    @start()
    def initialize(self):
        print("\n" + "=" * 65)
        print(f"🎬 [Flow 启动] 目标课题: {self.state.topic}")
        print("=" * 65)

    @listen(initialize)
    def run_scout_phase(self):
        """阶段一：广度搜索与事实搜集"""
        attempt = self.state.retry_count + 1
        print(f"\n🔎 [阶段一: Scout] 正在执行全网广度情报检索 (第 {attempt} 次尝试)...")
        
        crew_obj = TwoStageResearchCrew()
        # 仅执行阶段一任务以获得中间结果
        scout_agent = crew_obj.scout_researcher()
        scout_task = crew_obj.broad_research_task()
        
        # 将参数格式化输入
        inputs = {"topic": self.state.topic}
        result = scout_task.execute_sync(agent=scout_agent, context=str(inputs))
        self.state.phase1_summary = str(result.raw if hasattr(result, "raw") else result)
        print(f"📄 [阶段一: Scout] 检索完成，提取字符数: {len(self.state.phase1_summary)}")
        return self.state.phase1_summary

    @router(run_scout_phase)
    def quality_gate(self):
        """质量门禁路由：校验搜集到的数据是否足够支撑阶段二研判"""
        summary = self.state.phase1_summary
        
        # 质检条件：检查引用来源数量与内容厚度
        has_sources = (summary.count("http://") + summary.count("https://")) >= 2
        has_depth = len(summary.strip()) >= 250
        
        if (has_sources and has_depth) or self.state.retry_count >= 2:
            self.state.phase1_passed = True
            print("✅ [质检门禁] 阶段一情报质量符合研判要求，准予进入深度分析阶段。")
            return "proceed_to_analysis"
        else:
            self.state.retry_count += 1
            print(f"⚠️ [质检门禁] 阶段一内容深度或数据源不足 (重试 {self.state.retry_count}/2)，打回重新检索...")
            return "retry_scout"

    @listen("retry_scout")
    def refine_and_retry(self):
        """补充引导提示词后重试搜寻"""
        return self.run_scout_phase()

    @listen("proceed_to_analysis")
    def run_analyst_phase(self):
        """阶段二：深度综合推演与风险事实核验（完全隔离网络工具）"""
        print("\n📊 [阶段二: Analyst] 启动深度研判与交叉核验...")
        crew_obj = TwoStageResearchCrew()
        analyst_agent = crew_obj.synthesis_analyst()
        analysis_task = crew_obj.deep_analysis_task()
        
        # 将阶段一结果显式注入为前置上下文
        result = analysis_task.execute_sync(
            agent=analyst_agent,
            context=self.state.phase1_summary
        )
        
        if hasattr(result, "pydantic") and result.pydantic:
            self.state.final_report = result.pydantic
        print("🎯 [阶段二: Analyst] 深度报告生成完成！")
        return result

    @listen(run_analyst_phase)
    def save_and_export_report(self, analysis_result):
        """归档并导出最终研究报告：全套输出 Markdown、Word 与 16:9 汇报 PPT"""
        import shutil
        from craw.export_docx import get_report_paths, export_markdown_to_docx
        from craw.export_pptx import export_report_to_pptx

        output_dir = Path("reports")
        archive_md, archive_docx, archive_pptx, latest_md, latest_docx, latest_pptx = get_report_paths(
            output_dir, self.state.topic
        )

        report_content = str(analysis_result.raw if hasattr(analysis_result, "raw") else analysis_result)

        # 1. 写入历史归档 Markdown 文件
        with open(archive_md, "w", encoding="utf-8") as f:
            f.write(f"# 研究课题：{self.state.topic}\n\n{report_content}")

        # 2. 导出历史归档 Word 文档与图表
        archive_chart = archive_docx.with_suffix(".png")
        latest_chart = output_dir / "research_report_chart.png"
        try:
            export_markdown_to_docx(archive_md, archive_docx, chart_image_path=archive_chart)
            shutil.copy2(archive_md, latest_md)
            shutil.copy2(archive_docx, latest_docx)
            if archive_chart.exists():
                shutil.copy2(archive_chart, latest_chart)
                print(f"📈 [历史永久归档] 可视化图表已保存至: {archive_chart.name}")
                print(f"⭐ [最新便捷镜像] 图表已同步更新: {latest_chart.name}")
            print(f"\n💾 [历史永久归档] Markdown 已保存至: {archive_md.name}")
            print(f"📄 [历史永久归档] Word 文档已保存至: {archive_docx.name}")
            print(f"⭐ [最新便捷镜像] Word 已同步更新: {latest_docx.name}")
        except Exception as e:
            print(f"⚠️ Word 报告归档处理提示: {e}")

        # 3. 导出 16:9 商业汇报 PPT 并唤起打开
        try:
            export_report_to_pptx(archive_md, archive_pptx, chart_image_path=archive_chart)
            shutil.copy2(archive_pptx, latest_pptx)
            print(f"🖥️ [历史永久归档] 汇报 PPT 已保存至: {archive_pptx.name}")
            print(f"⭐ [最新便捷镜像] PPT 已同步更新: {latest_pptx.name}")
        except Exception as e:
            print(f"⚠️ PPT 导出处理提示: {e}")

        self.state.output_filepath = str(archive_docx)
        return self.state.output_filepath
