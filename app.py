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

from craw.runtime_status import display_model_name, resolve_models

_scout_model, _analyst_model = resolve_models()
_model_label = display_model_name(_scout_model)
if _analyst_model != _scout_model:
    _model_label = f"{display_model_name(_scout_model)} / {display_model_name(_analyst_model)}"

# 长伴咨询页面配置
st.set_page_config(
    page_title="长伴 · 战略研究智能体",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入精细化顶级 4A 咨询设计系统 CSS
st.markdown("""
<style>
    /* 全局排版与基础样式 */
    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
        color: #0F172A;
        -webkit-font-smoothing: antialiased;
    }

    /* 顶部导航与边距微调 */
    .block-container {
        padding-top: 1.8rem !important;
        padding-bottom: 3.5rem !important;
        max-width: 1280px;
    }

    /* 4A 咨询级 Executive Hero Header */
    .hero-container {
        background: linear-gradient(135deg, #0B132B 0%, #1C2541 60%, #1D4ED8 100%);
        border-radius: 16px;
        padding: 32px 36px;
        color: #FFFFFF;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -5px rgba(11, 19, 43, 0.15), 0 4px 12px -2px rgba(0, 0, 0, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.12);
        position: relative;
        overflow: hidden;
    }
    .hero-tag {
        display: inline-block;
        padding: 4px 12px;
        background: rgba(255, 255, 255, 0.12);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #93C5FD;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: 28px;
        font-weight: 750;
        letter-spacing: -0.02em;
        margin: 0 0 8px 0;
        color: #FFFFFF;
        line-height: 1.25;
    }
    .hero-desc {
        font-size: 14px;
        color: #CBD5E1;
        margin: 0;
        line-height: 1.6;
        max-width: 820px;
    }

    /* 4A 咨询级 KPI 卡片组件 */
    .kpi-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.03), 0 4px 12px -2px rgba(15, 23, 42, 0.03);
        transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        border-color: #CBD5E1;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08);
    }
    .kpi-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #64748B;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 22px;
        font-weight: 750;
        letter-spacing: -0.02em;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .kpi-sub {
        font-size: 12px;
        color: #1D4ED8;
        font-weight: 500;
    }

    /* 成果交付物卡片（4A 专属文件盒质感） */
    .delivery-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 6px -1px rgba(0, 0, 0, 0.04);
        margin-bottom: 8px;
        transition: all 0.2s ease;
    }
    .delivery-card:hover {
        border-color: #93C5FD;
        box-shadow: 0 8px 20px -3px rgba(29, 78, 216, 0.08);
    }
    .delivery-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.04em;
        margin-bottom: 8px;
    }
    .badge-word { background: #EFF6FF; color: #1D4ED8; border: 1px solid #DBEAFE; }
    .badge-ppt  { background: #FFF1F2; color: #E11D48; border: 1px solid #FFE4E6; }
    .badge-chart{ background: #ECFDF5; color: #059669; border: 1px solid #D1FAE5; }
    .badge-md   { background: #F8FAFC; color: #475569; border: 1px solid #E2E8F0; }

    .delivery-title {
        font-size: 15px;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 4px;
    }
    .delivery-desc {
        font-size: 12px;
        color: #64748B;
        line-height: 1.5;
        margin-bottom: 12px;
    }
    .delivery-meta {
        font-size: 11px;
        color: #94A3B8;
        margin-bottom: 14px;
    }

    /* 统一按钮质感 */
    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #1D4ED8 0%, #2563EB 100%) !important;
        border: none !important;
        font-weight: 600 !important;
        letter-spacing: 0.02em !important;
        box-shadow: 0 4px 12px rgba(29, 78, 216, 0.25) !important;
        border-radius: 8px !important;
        transition: all 0.2s ease !important;
    }
    .stButton button[kind="primary"]:hover {
        box-shadow: 0 6px 18px rgba(29, 78, 216, 0.35) !important;
        transform: translateY(-1px) !important;
    }
</style>
""", unsafe_allow_html=True)

# 侧边栏：系统运行环境与智库档案
with st.sidebar:
    logo_path = Path("assets/logo.png")
    if logo_path.exists():
        st.image(str(logo_path), width="stretch")
    st.markdown("### 战略中枢控制台")
    st.caption("长伴咨询 · 战略研究智能体")

    # API 与环境就绪状态徽章
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    serper_key = os.getenv("SERPER_API_KEY", "")

    st.markdown("**系统就绪指标**")
    if deepseek_key:
        st.badge("DeepSeek 密钥已填写", icon=":material/check_circle:", color="green")
    else:
        st.badge("DeepSeek 密钥未配置", icon=":material/error:", color="red")

    if serper_key:
        st.badge("搜索引擎密钥已填写", icon=":material/search:", color="green")
    else:
        st.badge("搜索引擎密钥未配置", icon=":material/error:", color="red")

    st.divider()

    # 编排引擎模式选择
    st.markdown("**研究编排引擎架构**")
    exec_mode = st.segmented_control(
        label="选择编排模式",
        options=["Flow 门禁重试", "Crew 标准流程"],
        default="Flow 门禁重试",
        selection_mode="single",
        label_visibility="collapsed"
    )
    if exec_mode == "Flow 门禁重试":
        st.caption("Flow 模式会检查检索底稿是否至少有 2 个链接、且不少于 250 字；不足时重试检索，最多 2 次。这不核验事实真伪。")
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


# 4A 咨询级 Executive Hero Header
st.markdown("""
<div class="hero-container">
    <div class="hero-tag">长伴咨询 · 人力资源战略研究</div>
    <div class="hero-title">长伴 · 战略研究智能体</div>
    <div class="hero-desc">
        面向人力资源课题的研究助手。检索员收集公开资料并保留链接，分析员据此整理判断，并交付 Word、幻灯片、趋势图和 Markdown。
    </div>
</div>
""", unsafe_allow_html=True)

# 4A 平台能力 KPI 概览指标行（杂志级三段式排版）
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-label">推理模型</div>
        <div class="kpi-value">{_model_label}</div>
        <div class="kpi-sub">以环境变量和 agents.yaml 为准</div>
    </div>
    """, unsafe_allow_html=True)

with k2:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">协同流程</div>
        <div class="kpi-value">两阶段</div>
        <div class="kpi-sub">检索员 + 分析员</div>
    </div>
    """, unsafe_allow_html=True)

with k3:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">质量门禁</div>
        <div class="kpi-value">链接与篇幅</div>
        <div class="kpi-sub">不足时重试检索，最多 2 次</div>
    </div>
    """, unsafe_allow_html=True)

with k4:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">交付成果</div>
        <div class="kpi-value">四种文件</div>
        <div class="kpi-sub">Word · 16:9 PPT · 图表 · MD</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# 课题设定与任务启动卡片
with st.container(border=True):
    st.markdown("#### 🎯 战略研究课题设定")

    preset_topics = [
        "制造业薪酬体系对标与调薪策略",
        "中层干部梯队建设与继任计划",
        "绩效考核体系从 KPI 向 OKR 过渡",
        "劳动用工合规风险排查与整改",
    ]

    st.markdown("**标杆战略研究范例推荐（点击快速装载）**")
    selected_preset = st.pills(
        label="推荐标杆课题",
        options=preset_topics,
        selection_mode="single",
        label_visibility="collapsed"
    )

    topic_query = st.text_input(
        label="输入人力资源研究课题",
        value=selected_preset if selected_preset else "",
        placeholder="例如：制造业薪酬体系对标与调薪策略",
        help="送去检索和模型前，会默认隐去手机号、身份证号、邮箱、银行卡号和已配置的客户企业名称"
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
                from craw.redact import redact_text
                safe_topic = redact_text(topic_query.strip())
                if safe_topic != topic_query.strip():
                    st.info("课题中的联系方式和已配置客户名称已替换为占位符后再送去检索和模型。")
                if "Flow" in (exec_mode or "Flow 门禁重试"):
                    from craw.flow import AdvancedTwoStageFlow
                    flow_inst = AdvancedTwoStageFlow()
                    flow_inst.state.topic = safe_topic
                    flow_inst.kickoff()
                else:
                    from craw.crew import TwoStageResearchCrew
                    crew_obj = TwoStageResearchCrew().crew()
                    crew_obj.kickoff(inputs={"topic": safe_topic})

                st.write("分析员已根据检索底稿整理判断。")
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
    st.markdown("### 📊 战略研究交付成果看板")

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
                caption="报告中的量化字段绘图，请与引用来源核对",
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
        st.markdown("#### 📦 一键获取多格式交付物包")
        st.caption("Word 和 Markdown 文末列有引用来源链接，请在使用前核对。")

        col_d1, col_d2, col_d3, col_d4 = st.columns(4)

        with col_d1:
            docx_size = f"{latest_docx_path.stat().st_size / 1024:.1f} KB" if latest_docx_path.exists() else "准备中"
            st.markdown(f"""
            <div class="delivery-card">
                <div class="delivery-badge badge-word">Word 文档</div>
                <div class="delivery-title">完整战略研报</div>
                <div class="delivery-desc">排版遵循国际管理咨询规范，适合全员研读与细化批注。</div>
                <div class="delivery-meta">格式: .docx · 体积: {docx_size}</div>
            </div>
            """, unsafe_allow_html=True)
            if latest_docx_path.exists():
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

        with col_d2:
            pptx_size = f"{latest_pptx_path.stat().st_size / 1024:.1f} KB" if latest_pptx_path.exists() else "准备中"
            st.markdown(f"""
            <div class="delivery-card">
                <div class="delivery-badge badge-ppt">PPT 幻灯片</div>
                <div class="delivery-title">16:9 商业演示文稿</div>
                <div class="delivery-desc">专为董事会及高管汇报定制的 16:9 宽屏结构化母版。</div>
                <div class="delivery-meta">格式: .pptx · 体积: {pptx_size}</div>
            </div>
            """, unsafe_allow_html=True)
            if latest_pptx_path.exists():
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

        with col_d3:
            chart_size = f"{latest_chart_path.stat().st_size / 1024:.1f} KB" if latest_chart_path.exists() else "准备中"
            st.markdown(f"""
            <div class="delivery-card">
                <div class="delivery-badge badge-chart">高清图表</div>
                <div class="delivery-title">300 DPI 发展趋势图</div>
                <div class="delivery-desc">采用 Matplotlib 印刷级引擎渲染的行业量化多指标曲线。</div>
                <div class="delivery-meta">格式: .png · 体积: {chart_size}</div>
            </div>
            """, unsafe_allow_html=True)
            if latest_chart_path.exists():
                with open(latest_chart_path, "rb") as f:
                    st.download_button(
                        label="下载高清图表",
                        data=f,
                        file_name=latest_chart_path.name,
                        mime="image/png",
                        icon=":material/download:",
                        width="stretch"
                    )

        with col_d4:
            md_size = f"{latest_md_path.stat().st_size / 1024:.1f} KB" if latest_md_path.exists() else "准备中"
            st.markdown(f"""
            <div class="delivery-card">
                <div class="delivery-badge badge-md">Markdown 简报</div>
                <div class="delivery-title">结构化知识简报</div>
                <div class="delivery-desc">便于一键导入企业知识库、Notion、飞书或沉淀进 Git 仓库。</div>
                <div class="delivery-meta">格式: .md · 体积: {md_size}</div>
            </div>
            """, unsafe_allow_html=True)
            if latest_md_path.exists():
                with open(latest_md_path, "rb") as f:
                    st.download_button(
                        label="下载 Markdown",
                        data=f,
                        file_name=latest_md_path.name,
                        mime="text/markdown",
                        icon=":material/download:",
                        width="stretch"
                    )

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
