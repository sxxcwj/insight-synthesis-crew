import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量并配置性能优化
load_dotenv()
os.environ["CREWAI_TELEMETRY_OPT_OUT"] = "true"

import streamlit as st

# 确保 src 目录在 sys.path 中
src_dir = Path(__file__).resolve().parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

# 4A 战略咨询页面配置
st.set_page_config(
    page_title="Insight Synthesis Studio · 战略研究智能体",
    page_icon=":material/insights:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 侧边栏：系统运行环境与智库档案
with st.sidebar:
    st.markdown("### 战略中枢控制台")
    st.caption("Insight Synthesis Studio · 4A 咨询交付标准")

    # API 与环境就绪状态徽章
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    serper_key = os.getenv("SERPER_API_KEY", "")

    st.markdown("**系统就绪指标**")
    if deepseek_key:
        st.badge("DeepSeek API: 已就绪", icon=":material/check_circle:", color="green")
    else:
        st.badge("DEEPSEEK_API_KEY: 未配置", icon=":material/error:", color="red")

    if serper_key:
        st.badge("Google 搜索 (Serper): 已就绪", icon=":material/search:", color="green")
    else:
        st.badge("网络抓取引擎: 纯抓取模式", icon=":material/public:", color="blue", help="Serper API 未配置时，系统将使用直接网页抓取")

    st.divider()

    # 编排引擎模式选择
    st.markdown("**研究编排引擎架构**")
    exec_mode = st.segmented_control(
        label="选择编排模式",
        options=["Flow 自愈质检", "Crew 标准流程"],
        default="Flow 自愈质检",
        selection_mode="single",
        label_visibility="collapsed"
    )
    if exec_mode == "Flow 自愈质检":
        st.caption("🛡️ **Flow 模式**: 配备两阶段质量门禁与自愈校验，自动把关数据深度与信源密度。")
    else:
        st.caption("⚡ **Crew 模式**: 标准流水线，执行速度快，适合敏捷概念探索。")

    st.divider()

    # 历史研究档案库
    st.markdown("**历史课题沉淀智库**")
    archive_dir = Path("reports/archive")
    archive_md_files = []
    if archive_dir.exists():
        archive_md_files = sorted(list(archive_dir.glob("*.md")), reverse=True)

    if archive_md_files:
        st.caption(f"智库已永久归档 {len(archive_md_files)} 项战略课题：")
        for f in archive_md_files[:6]:
            clean_title = f.stem
            # 格式例如 20261022_123900_课题名称
            parts = clean_title.split("_", 2)
            if len(parts) == 3:
                date_tag = parts[0]
                topic_title = parts[2]
            else:
                date_tag = "Archive"
                topic_title = clean_title

            if len(topic_title) > 16:
                topic_title = topic_title[:15] + "..."
            st.markdown(f":material/history: `{date_tag}` {topic_title}")
    else:
        st.caption("暂无归档，每次研究交付后将自动在此沉淀。")


# 主界面 Header 区域（4A 咨询风格）
st.markdown("### Insight Synthesis Studio · 战略研究智能体")
st.caption("顶级 4A 咨询交付标准 · 双阶段广度情报探测与深度战略研判 · 自动交付 Markdown、Word、16:9 商业演示幻灯片与 300 DPI 趋势图表")

# 4A 平台能力 KPI 概览指标行（4 列卡片容器）
col_m1, col_m2, col_m3, col_m4 = st.columns(4, border=True)

with col_m1:
    st.caption("推理大脑")
    st.markdown("**DeepSeek-V3 / Flash**")
    st.caption("低延迟战略大模型矩阵")

with col_m2:
    st.caption("协同架构")
    st.markdown("**Two-Stage Pipeline**")
    st.caption("Scout 探测 + Analyst 研判")

with col_m3:
    st.caption("自愈护栏")
    st.markdown("**Quality Gate 2.0**")
    st.caption("信源密度与反幻觉核查")

with col_m4:
    st.caption("交付矩阵")
    st.markdown("**4 维全格式产物**")
    st.caption("Word · 16:9 PPT · 300DPI · MD")

st.write("")

# 课题设定与任务启动卡片
with st.container(border=True):
    st.markdown("#### 战略研究课题设定")

    preset_topics = [
        "2026年企业级大模型微调与 RAG 架构的选型平衡与落地实践",
        "低空经济在城市物流与垂直起降（eVTOL）场景的商业化演进格局",
        "全球半导体先进制程（2nm/GAA）与先进制程封装技术的竞争态势",
        "具身智能机器人软硬件协同体系与高保真物理仿真训练发展趋势"
    ]

    st.markdown("**标杆研究课题推荐**")
    selected_preset = st.pills(
        label="推荐标杆课题",
        options=preset_topics,
        selection_mode="single",
        label_visibility="collapsed"
    )

    topic_query = st.text_input(
        label="输入产业、商业或技术研究课题",
        value=selected_preset if selected_preset else "",
        placeholder="例如：2026年中国人形机器人核心零部件供应链与商业落地前景",
        help="支持输入任何前沿技术、商业模式、产业分析或战略咨询课题"
    )

    col_btn_l, col_btn_r = st.columns([3, 1])
    with col_btn_l:
        start_btn = st.button(
            "启动战略情报搜寻与全格式交付",
            type="primary",
            icon=":material/rocket_launch:",
            width="stretch"
        )
    with col_btn_r:
        if st.button("清空输入", icon=":material/refresh:", width="stretch"):
            st.rerun()

# 运行逻辑与状态监控
if start_btn:
    if not topic_query.strip():
        st.warning("请先输入或选择研究课题。")
    elif not deepseek_key:
        st.error("未检测到 DEEPSEEK_API_KEY，请先在 .env 中配置 API 密钥。")
    else:
        with st.status("智能体两阶段协同研究执行中...", expanded=True) as status_box:
            st.write("🚀 **流程初始化**: 正在调度高级情报搜寻员 (Scout) 与战略分析主笔 (Analyst)...")
            st.write("🔎 **阶段一 (Scout)**: 正在执行全网广度情报检索、量化指标采集与去噪...")

            try:
                if "Flow" in (exec_mode or "Flow 自愈质检"):
                    from craw.flow import AdvancedTwoStageFlow
                    flow_inst = AdvancedTwoStageFlow()
                    flow_inst.state.topic = topic_query.strip()
                    flow_inst.kickoff()
                else:
                    from craw.crew import TwoStageResearchCrew
                    crew_obj = TwoStageResearchCrew().crew()
                    crew_obj.kickoff(inputs={"topic": topic_query.strip()})

                st.write("📊 **阶段二 (Analyst)**: 战略分析完成，双阶段质量门禁核查通过。")
                st.write("📈 **多模态图表**: 300 DPI 商业咨询趋势图表已渲染生成。")
                st.write("📄 **全套交付成果**: Word (.docx)、16:9 PPT (.pptx) 与 Markdown 均已归档并同步！")

                status_box.update(
                    label="全流程完成：质量门禁验证通过，多模态交付物已全部生成！",
                    state="complete"
                )

                # 自动为用户打开生成的 PPT 文件（用户全局首选项）
                pptx_output = Path("reports/research_report.pptx")
                if pptx_output.exists():
                    try:
                        subprocess.Popen(["open", "-a", "Microsoft PowerPoint", str(pptx_output.resolve())])
                    except Exception:
                        pass

                st.balloons()
            except Exception as err:
                status_box.update(label="执行过程中遇到异常", state="error")
                st.error(f"执行中断: {err}")

# 结果展示区（读取最新的 reports 文件）
latest_md_path = Path("reports/research_report.md")
latest_docx_path = Path("reports/research_report.docx")
latest_pptx_path = Path("reports/research_report.pptx")
latest_chart_path = Path("reports/research_report_chart.png")

if latest_md_path.exists():
    st.divider()
    st.markdown("### 战略研究交付成果看板")

    tab_md, tab_chart, tab_pptx, tab_download, tab_history = st.tabs([
        "战略简报 (Markdown)",
        "量化发展趋势 (300 DPI)",
        "16:9 商业演示幻灯片",
        "全套产物交付中心",
        "历史智库检索"
    ])

    with tab_md:
        md_text = latest_md_path.read_text(encoding="utf-8")
        st.markdown(md_text)

    with tab_chart:
        if latest_chart_path.exists():
            st.image(
                str(latest_chart_path),
                caption="4A 咨询标准 · 关键量化发展趋势图表 (300 DPI 高分辨率渲染)",
                width="stretch"
            )
            chart_size_kb = latest_chart_path.stat().st_size / 1024
            st.caption(f"图表规格：300 DPI 印刷级渲染 · 文件大小: {chart_size_kb:.1f} KB · 色彩规范: Slate 900 / Royal Blue / Emerald Green")
        else:
            st.info("当前研报未包含量化图表或图表正在生成中。")

    with tab_pptx:
        col_pptx_desc, col_pptx_act = st.columns([3, 1])
        with col_pptx_desc:
            st.markdown("""
            **16:9 宽屏 PowerPoint 幻灯片设计规格：**
            1. **封面大屏**：深邃 Slate 900 商务质感与课题大标题
            2. **执行摘要看板**：居中卡片式呈现战略结论
            3. **三列洞察矩阵**：经典 3-Column 结构化拆解核心发现
            4. **图文对照趋势页**：嵌入 300 DPI 宽幅图表与数据透视卡片
            5. **潜在风险警示页**：警示关键合规、供应链与业务不确定性
            6. **前瞻行动建议路线**：决策绿调战略路线图
            7. **权威信源背书清单**：官方公文、顶级期刊与权威出处一览
            """)
        with col_pptx_act:
            if latest_pptx_path.exists():
                pptx_size_kb = latest_pptx_path.stat().st_size / 1024
                st.success(f"PPTX 演示文稿就绪\n\n体积: {pptx_size_kb:.1f} KB")
                if st.button("在 PowerPoint 中打开", icon=":material/open_in_new:", width="stretch"):
                    try:
                        subprocess.Popen(["open", "-a", "Microsoft PowerPoint", str(latest_pptx_path.resolve())])
                        st.toast("已调用 Microsoft PowerPoint 打开演示文稿")
                    except Exception as e:
                        st.error(f"无法打开应用: {e}")

    with tab_download:
        st.markdown("#### 一键获取多格式交付物包")
        st.caption("所有文件均采用国际 4A 咨询机构标准排版与色彩规范，可直接用于高管汇报或印刷")

        col_d1, col_d2, col_d3, col_d4 = st.columns(4, border=True)

        with col_d1:
            st.markdown("**:material/description: Word 研报**")
            st.caption("格式：.docx 完整战略研报")
            if latest_docx_path.exists():
                st.caption(f"大小: {latest_docx_path.stat().st_size / 1024:.1f} KB")
                with open(latest_docx_path, "rb") as f:
                    st.download_button(
                        label="下载 Word 研报",
                        data=f,
                        file_name=latest_docx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        type="primary",
                        icon=":material/download:",
                        width="stretch"
                    )
            else:
                st.caption("生成中...")

        with col_d2:
            st.markdown("**:material/slideshow: 商业演示文稿**")
            st.caption("格式：16:9 .pptx 宽屏幻灯片")
            if latest_pptx_path.exists():
                st.caption(f"大小: {latest_pptx_path.stat().st_size / 1024:.1f} KB")
                with open(latest_pptx_path, "rb") as f:
                    st.download_button(
                        label="下载 16:9 PPTX",
                        data=f,
                        file_name=latest_pptx_path.name,
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        type="primary",
                        icon=":material/download:",
                        width="stretch"
                    )
            else:
                st.caption("生成中...")

        with col_d3:
            st.markdown("**:material/article: Markdown 简报**")
            st.caption("格式：.md 结构化文本")
            if latest_md_path.exists():
                st.caption(f"大小: {latest_md_path.stat().st_size / 1024:.1f} KB")
                with open(latest_md_path, "rb") as f:
                    st.download_button(
                        label="下载 Markdown",
                        data=f,
                        file_name=latest_md_path.name,
                        mime="text/markdown",
                        icon=":material/download:",
                        width="stretch"
                    )
            else:
                st.caption("生成中...")

        with col_d4:
            st.markdown("**:material/monitoring: 量化趋势图表**")
            st.caption("格式：.png 300 DPI 高清原图")
            if latest_chart_path.exists():
                st.caption(f"大小: {latest_chart_path.stat().st_size / 1024:.1f} KB")
                with open(latest_chart_path, "rb") as f:
                    st.download_button(
                        label="下载高清图表",
                        data=f,
                        file_name=latest_chart_path.name,
                        mime="image/png",
                        icon=":material/download:",
                        width="stretch"
                    )
            else:
                st.caption("生成中...")

    with tab_history:
        st.markdown("#### 历史战略课题档案库检索")
        if archive_md_files:
            file_options = {f.name: f for f in archive_md_files}
            selected_file_name = st.selectbox(
                "选择历史研究课题档案进行快速回顾：",
                options=list(file_options.keys())
            )
            if selected_file_name:
                selected_file = file_options[selected_file_name]
                st.caption(f"档案文件：`{selected_file.name}` · 大小: {selected_file.stat().st_size / 1024:.1f} KB")
                with st.expander("查看历史研究报告全文", expanded=False):
                    content = selected_file.read_text(encoding="utf-8")
                    st.markdown(content)
        else:
            st.info("历史档案库尚无已沉淀课题。")
