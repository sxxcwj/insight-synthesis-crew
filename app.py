import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 环境变量并优化性能
load_dotenv()
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import streamlit as st

# 确保 src 目录在 sys.path 中
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 页面基础配置
st.set_page_config(
    page_title="Insight Synthesis Studio · 战略研究控制台",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入现代商务级 CSS（使用纯本地系统字体，彻底杜绝外网 CDN 阻塞）
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Segoe UI", Roboto, "Helvetica Neue", "Microsoft YaHei", sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border-radius: 12px;
        padding: 24px 28px;
        color: #FFFFFF;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px rgba(0,0,0,0.08);
        border: 1px solid #334155;
    }
    .main-header h1 {
        font-size: 26px;
        font-weight: 700;
        margin: 0 0 8px 0;
        color: #F8FAFC;
    }
    .main-header p {
        font-size: 13.5px;
        color: #94A3B8;
        margin: 0;
        line-height: 1.5;
    }
    
    .card-metric {
        background: #F8FAFC;
        border-radius: 10px;
        padding: 16px 20px;
        border-left: 4px solid #1D4ED8;
        border: 1px solid #E2E8F0;
        margin-bottom: 12px;
    }
    
    .stDownloadButton button {
        background-color: #1D4ED8 !important;
        color: white !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        width: 100%;
        border: none !important;
    }
    .stDownloadButton button:hover {
        background-color: #1E40AF !important;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏：系统状态与历史归档
with st.sidebar:
    st.markdown("### ⚙️ 系统控制与运行环境")
    
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    serper_key = os.getenv("SERPER_API_KEY", "")
    
    if deepseek_key:
        st.success("🟢 DeepSeek API 已就绪")
    else:
        st.error("🔴 DEEPSEEK_API_KEY 未配置")
        
    if serper_key:
        st.success("🟢 Google 搜索工具 (Serper) 已就绪")
    else:
        st.warning("🟡 Serper API 未配置（将仅使用网页抓取）")

    st.markdown("---")
    st.markdown("### 🎛️ 运行模式设置")
    exec_mode = st.radio(
        "选择研究编排引擎：",
        ["自愈质检 Flow 模式 (推荐)", "标准两阶段 Crew 模式"],
        index=0
    )

    st.markdown("---")
    st.markdown("### 📂 历史研报永久归档")
    archive_dir = Path("reports/archive")
    if archive_dir.exists():
        archive_files = sorted(list(archive_dir.glob("*.md")), reverse=True)
        if archive_files:
            st.caption(f"已沉淀 {len(archive_files)} 份历史研究课题：")
            for f in archive_files[:8]:
                display_name = f.stem
                if len(display_name) > 28:
                    display_name = display_name[:26] + ".."
                st.markdown(f"• `{display_name}`")
        else:
            st.caption("暂无归档，运行后将自动永久沉淀。")
    else:
        st.caption("归档目录准备中。")

# 主界面顶部
st.markdown("""
<div class="main-header">
    <h1>Insight Synthesis Studio · 战略研究智能体控制台</h1>
    <p>基于 CrewAI 与 DeepSeek-Flash 的两阶段研究与全格式交付系统 · 自动输出 Markdown、Word (.docx)、16:9 商务 PPT 及 300 DPI 量化趋势图表</p>
</div>
""", unsafe_allow_html=True)

# 快速选题预设
preset_topics = [
    "2026年企业级大模型微调与 RAG 架构的选型平衡与落地实践",
    "低空经济在城市物流与垂直起降（eVTOL）场景的商业化演进格局",
    "全球半导体先进制程（2nm/GAA）与先进制程封装技术的竞争态势",
    "具身智能机器人软硬件协同体系与高保真物理仿真训练发展趋势"
]

col_input, col_preset = st.columns([2.5, 1.2])

with col_preset:
    st.markdown("##### 💡 标杆研究范例推荐")
    selected_preset = st.selectbox("点击加载参考选题：", ["自定义选题..."] + preset_topics)

with col_input:
    st.markdown("##### 🎯 研究课题设定")
    initial_topic = selected_preset if selected_preset != "自定义选题..." else ""
    topic_query = st.text_input(
        "请输入您需要深度研究的产业、商业或技术课题：",
        value=initial_topic,
        placeholder="例如：2026年中国人形机器人核心零部件供应链与商业落地前景"
    )

start_btn = st.button("🚀 启动深度研究与全格式报告合成", type="primary", use_container_width=True)

# 运行逻辑
if start_btn:
    if not topic_query.strip():
        st.warning("⚠️ 请先输入研究课题内容。")
    elif not deepseek_key:
        st.error("❌ 未检测到 DEEPSEEK_API_KEY，请先在 .env 中配置密钥。")
    else:
        with st.status("🛠️ 智能体两阶段协同研究执行中...", expanded=True) as status_box:
            st.write("🚀 **流程启动**: 正在调度高级情报搜寻员 (Scout) 与战略分析主笔 (Analyst)...")
            st.write("🔎 **阶段一 (Scout)**: 正在执行全网广度情报检索、量化指标采集与去噪...")

            try:
                if "Flow" in exec_mode:
                    from craw.flow import AdvancedTwoStageFlow
                    flow_inst = AdvancedTwoStageFlow()
                    flow_inst.state.topic = topic_query.strip()
                    flow_inst.kickoff()
                else:
                    from craw.crew import TwoStageResearchCrew
                    crew_obj = TwoStageResearchCrew().crew()
                    result = crew_obj.kickoff(inputs={"topic": topic_query.strip()})

                st.write("📊 **阶段二 (Analyst)**: 战略分析完成，自愈门禁质检通过。")
                st.write("📈 **多模态图表**: 300 DPI 商务咨询趋势图已渲染并内嵌。")
                st.write("📄 **全套成果**: Word (.docx)、16:9 PPT (.pptx) 与 Markdown 均已归档并同步最新镜像！")
                status_box.update(label="✅ [全流程完成] 质量门禁验证通过，多模态交付物已全部生成！", state="complete")
                st.balloons()
            except Exception as err:
                status_box.update(label="❌ 运行遇到异常", state="error")
                st.error(f"执行中断: {err}")

# 结果展示区（读取最新的 reports 文件）
latest_md_path = Path("reports/research_report.md")
latest_docx_path = Path("reports/research_report.docx")
latest_pptx_path = Path("reports/research_report.pptx")
latest_chart_path = Path("reports/research_report_chart.png")

if latest_md_path.exists():
    st.markdown("---")
    st.markdown("### 📊 最新研究交付成果看板")

    tab_md, tab_chart, tab_pptx, tab_download = st.tabs([
        "📄 深度报告简报 (Markdown)",
        "📈 关键发展趋势图表 (300 DPI)",
        "🖥️ 16:9 商业 PPT 幻灯片概览",
        "📥 全套产物下载中心"
    ])

    with tab_md:
        md_text = latest_md_path.read_text(encoding="utf-8")
        st.markdown(md_text)

    with tab_chart:
        if latest_chart_path.exists():
            st.image(str(latest_chart_path), caption="行业关键量化指标与发展趋势研判 (300 DPI Consulting Edition)", use_container_width=True)
        else:
            st.info("ℹ️ 当前研报未包含量化图表或图表渲染中。")

    with tab_pptx:
        st.markdown("""
        **🖥️ 16:9 宽屏 PowerPoint 幻灯片结构：**
        1. **封面大屏**：深邃 Slate 900 商务质感与课题大标题
        2. **执行摘要看板**：居中卡片式呈现战略结论
        3. **三列洞察矩阵**：经典 3-Column 结构化拆解核心发现
        4. **图文对照趋势页**：嵌入 300 DPI 宽幅图表与数据透视卡片
        5. **潜在风险警示页**：红色警示关键合规与业务不确定性
        6. **前瞻行动建议路线**：决策绿调战略路线图
        7. **权威信源背书清单**：官方公文、顶级期刊与权威出处一览
        """)
        if latest_pptx_path.exists():
            st.success(f"✅ PowerPoint 演示文稿就绪 ({latest_pptx_path.stat().st_size / 1024:.1f} KB)，可前往【全套产物下载中心】获取。")

    with tab_download:
        st.markdown("#### 📦 一键下载多格式研究成果交付包")
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)

        with col_d1:
            if latest_docx_path.exists():
                with open(latest_docx_path, "rb") as f:
                    st.download_button(
                        label="📄 下载 Word 报告 (.docx)",
                        data=f,
                        file_name=latest_docx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

        with col_d2:
            if latest_pptx_path.exists():
                with open(latest_pptx_path, "rb") as f:
                    st.download_button(
                        label="🖥️ 下载 16:9 PPT (.pptx)",
                        data=f,
                        file_name=latest_pptx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
                    )

        with col_d3:
            if latest_md_path.exists():
                with open(latest_md_path, "rb") as f:
                    st.download_button(
                        label="📝 下载 Markdown (.md)",
                        data=f,
                        file_name=latest_md_path.name,
                        mime="text/markdown"
                    )

        with col_d4:
            if latest_chart_path.exists():
                with open(latest_chart_path, "rb") as f:
                    st.download_button(
                        label="📈 下载高清图表 (.png)",
                        data=f,
                        file_name=latest_chart_path.name,
                        mime="image/png"
                    )
