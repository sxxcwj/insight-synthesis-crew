from typing import List, Optional
from pydantic import BaseModel, Field


class KeyInsight(BaseModel):
    title: str = Field(description="核心发现或洞察要点标题")
    details: str = Field(description="详细论证、数据指标或案例支撑")


class CitationSource(BaseModel):
    title: str = Field(description="来源机构、论文或报告标题（例如：中国民航局、新华社、工信部、McKinsey等）")
    url: str = Field(description="权威引用网页链接或论文原始 URL")
    evidence: str = Field(description="该来源支撑的核心论据或关键事实点摘要")


class QuantitativeMetric(BaseModel):
    label: str = Field(description="指标或维度名称（例如年份 2024、技术路线、市场主体等）")
    value: float = Field(description="数值大小（如市场规模数值、渗透率百分比等）")
    unit: str = Field(default="", description="单位（如亿元、%、万台、Gbps等）")


class QuantitativeChart(BaseModel):
    chart_title: str = Field(description="图表标题（例如：2024-2030年行业市场规模及增长预测）")
    chart_type: str = Field(default="bar", description="图表类型：bar（对比柱状图）或 line（趋势折线图）")
    x_axis_label: str = Field(default="", description="横轴维度说明")
    y_axis_label: str = Field(default="", description="纵轴标签（含单位）")
    data_points: List[QuantitativeMetric] = Field(default_factory=list, description="用于绘图的关键量化数据点列表（建议3-6个点）")
    takeaway: str = Field(default="", description="该图表揭示的战略洞察核心要点总结")


class FinalResearchReport(BaseModel):
    topic: str = Field(description="研究主题")
    executive_summary: str = Field(description="高层执行摘要（200-300字）")
    key_findings: List[KeyInsight] = Field(description="核心发现与洞察列表（3个核心要点）")
    risk_assessment: List[str] = Field(description="潜在风险与不确定性分析（至少2项）")
    strategic_recommendations: List[str] = Field(description="面向决策者的前瞻性战略行动建议")
    quantitative_chart: Optional[QuantitativeChart] = Field(
        default=None,
        description="报告中的关键量化指标与趋势数据序列，供多模态图表引擎渲染为可视化图表"
    )
    sources: List[CitationSource] = Field(
        default_factory=list,
        description="报告引用的权威来源、政策公文、白皮书与真实网页链接清单（至少3-6项，绝不能遗漏）"
    )
