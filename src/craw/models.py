from typing import List
from pydantic import BaseModel, Field


class KeyInsight(BaseModel):
    title: str = Field(description="核心发现或洞察要点标题")
    details: str = Field(description="详细论证、数据指标或案例支撑")


class CitationSource(BaseModel):
    title: str = Field(description="来源机构、论文或报告标题（例如：中国民航局、新华社、工信部、McKinsey等）")
    url: str = Field(description="权威引用网页链接或论文原始 URL")
    evidence: str = Field(description="该来源支撑的核心论据或关键事实点摘要")


class FinalResearchReport(BaseModel):
    topic: str = Field(description="研究主题")
    executive_summary: str = Field(description="高层执行摘要（200-300字）")
    key_findings: List[KeyInsight] = Field(description="核心发现与洞察列表（3个核心要点）")
    risk_assessment: List[str] = Field(description="潜在风险与不确定性分析（至少2项）")
    strategic_recommendations: List[str] = Field(description="面向决策者的前瞻性战略行动建议")
    sources: List[CitationSource] = Field(
        default_factory=list,
        description="报告引用的权威来源、政策公文、白皮书与真实网页链接清单（至少3-6项，绝不能遗漏）"
    )
