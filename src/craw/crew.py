import os
from pathlib import Path
from typing import Tuple, Any
from dotenv import load_dotenv
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, FileReadTool

from craw.models import FinalResearchReport

load_dotenv()
os.environ.setdefault("CREWAI_TELEMETRY_OPT_OUT", "true")

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"


def validate_scout_quality(output: Any) -> Tuple[bool, Any]:
    """质量守卫 Guardrail：核验阶段一产出是否具备基本的事实丰度与引用链接"""
    content = str(output)
    if len(content.strip()) < 200:
        return (False, "阶段一搜集信息过少，请补充具体的事实背景与关键数据指标。")
    return (True, output)


@CrewBase
class TwoStageResearchCrew:
    """两阶段协同研究 Crew"""

    agents_config = str(CONFIG_DIR / "agents.yaml")
    tasks_config = str(CONFIG_DIR / "tasks.yaml")

    # ================= 阶段一：广度信息搜集员 =================
    @agent
    def scout_researcher(self) -> Agent:
        tools = []
        # 如果配置了 SERPER_API_KEY 则启用，同时启用网页内容抓取
        if os.getenv("SERPER_API_KEY"):
            tools.append(SerperDevTool(n_results=5))
        tools.append(ScrapeWebsiteTool())

        cfg = self.agents_config["scout_researcher"]
        llm_model = os.getenv("SCOUT_LLM_MODEL", cfg.get("llm", "deepseek/deepseek-flash"))
        return Agent(
            config=cfg,
            tools=tools,
            llm=llm_model,
        )

    # ================= 阶段二：深度综合分析员 =================
    @agent
    def synthesis_analyst(self) -> Agent:
        cfg = self.agents_config["synthesis_analyst"]
        llm_model = os.getenv("ANALYST_LLM_MODEL", cfg.get("llm", "deepseek/deepseek-flash"))
        return Agent(
            config=cfg,
            # 严格限制：仅提供本地受控文件读取，阻断公网搜索工具，杜绝发散与幻觉
            tools=[FileReadTool()],
            llm=llm_model,
        )

    # ================= 任务链路编排 =================
    @task
    def broad_research_task(self) -> Task:
        return Task(
            config=self.tasks_config["broad_research_task"],
            agent=self.scout_researcher(),
            guardrail=validate_scout_quality,
            max_retries=2,
        )

    @task
    def deep_analysis_task(self) -> Task:
        return Task(
            config=self.tasks_config["deep_analysis_task"],
            agent=self.synthesis_analyst(),
            context=[self.broad_research_task()],  # 将阶段一结果作为唯一前置上下文
            output_pydantic=FinalResearchReport,   # 结构化数据约束
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,  # 线性两阶段顺序流转
            verbose=True,
        )
