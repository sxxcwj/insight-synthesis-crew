import re
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

import matplotlib
# 使用非交互式后端，避免在无 GUI 或多线程环境中报错
matplotlib.use("Agg")
import matplotlib.pyplot as plt


# 配置中文字体与负号显示
plt.rcParams["font.sans-serif"] = [
    "PingFang SC",
    "PingFang TC",
    "Heiti SC",
    "Arial Unicode MS",
    "Microsoft YaHei",
    "SimHei",
    "sans-serif",
]
plt.rcParams["axes.unicode_minus"] = False


def extract_chart_data_from_report(md_or_data: Any) -> Optional[Dict[str, Any]]:
    """
    从结构化字典或 Markdown 中提取或解析量化图表数据
    """
    data = None
    if isinstance(md_or_data, dict):
        data = md_or_data
    elif isinstance(md_or_data, (Path, str)):
        content = Path(md_or_data).read_text(encoding="utf-8") if isinstance(md_or_data, Path) else str(md_or_data)
        # 优先提取 JSON
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                data = json.loads(m.group(0))
            except Exception:
                data = None

    if data and "quantitative_chart" in data and data["quantitative_chart"]:
        chart_obj = data["quantitative_chart"]
        if isinstance(chart_obj, dict) and chart_obj.get("data_points"):
            return chart_obj

    # 兜底：若未显式提供图表数据，则从核心洞察文本中智能检索量化年份与数值
    if data and "key_findings" in data and data["key_findings"]:
        points = []
        for finding in data["key_findings"]:
            text = finding.get("details", "") if isinstance(finding, dict) else str(finding)
            # 匹配类似 "2024年...1200亿" 或 "2025年达 35%"
            matches = re.findall(r"(202\d)年[^\d]{0,10}(\d+(?:\.\d+)?)\s*(亿元|万台|万套|%|吉瓦|GW)?", text)
            for year, val, unit in matches:
                points.append({
                    "label": f"{year}年",
                    "value": float(val),
                    "unit": unit or ""
                })
        if len(points) >= 3:
            return {
                "chart_title": f"{data.get('topic', '核心课题')}·关键发展趋势指标",
                "chart_type": "line" if "年" in points[0]["label"] else "bar",
                "x_axis_label": "时间周期",
                "y_axis_label": points[0]["unit"] or "指标数值",
                "data_points": points[:6],
                "takeaway": "核心指标显示出强劲的增长韧性与规模化扩张潜力。"
            }

    return None


def render_consulting_chart(chart_info: Dict[str, Any], output_path: Path) -> Path:
    """
    使用咨询级视觉规范渲染高分辨率图表 (300 DPI)
    风格：McKinsey / BCG 极简专业风、冷调克制配色、清晰数据标签
    """
    title = chart_info.get("chart_title", "量化指标趋势概览")
    chart_type = chart_info.get("chart_type", "bar").lower()
    x_label = chart_info.get("x_axis_label", "")
    y_label = chart_info.get("y_axis_label", "")
    takeaway = chart_info.get("takeaway", "")
    points = chart_info.get("data_points", [])

    if not points:
        raise ValueError("图表数据点为空，无法绘制")

    labels = [p.get("label", str(i+1)) for i, p in enumerate(points)]
    values = [float(p.get("value", 0)) for p in points]
    units = [p.get("unit", "") for p in points]
    primary_unit = units[0] if units and units[0] else ""

    # 画布比例：16:9 (8 x 4.5 英寸)，适合 PPT 与 Word 排版
    fig, ax = plt.subplots(figsize=(8.5, 4.8), dpi=300)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFCFF")

    # 咨询级配色板
    COLOR_PRIMARY = "#1D4ED8"     # Royal Blue
    COLOR_SECONDARY = "#3B82F6"   # Slate Blue
    COLOR_HIGHLIGHT = "#0284C7"   # Sky Blue
    COLOR_DARK = "#0F172A"        # Slate 900
    COLOR_MUTED = "#64748B"       # Slate 500
    COLOR_GRID = "#E2E8F0"        # Light Grid

    if chart_type == "line":
        # 折线趋势图
        ax.plot(
            labels, values,
            color=COLOR_PRIMARY,
            linewidth=3.2,
            marker="o",
            markersize=8,
            markerfacecolor="#FFFFFF",
            markeredgecolor=COLOR_PRIMARY,
            markeredgewidth=2.5,
            zorder=4,
            label="趋势线"
        )
        # 面积柔和渐变微底色
        ax.fill_between(labels, values, color=COLOR_HIGHLIGHT, alpha=0.12, zorder=3)

        # 标注各数据点具体数值
        for i, (val, unit) in enumerate(zip(values, units)):
            u = unit or primary_unit
            val_str = f"{int(val)}" if val.is_integer() else f"{val:.1f}"
            ax.annotate(
                f"{val_str}{u}",
                xy=(i, val),
                xytext=(0, 10),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=10.5,
                fontweight="bold",
                color=COLOR_DARK,
                bbox=dict(boxstyle="round,pad=0.25", fc="#FFFFFF", ec=COLOR_GRID, lw=0.8, alpha=0.95),
                zorder=5
            )
    else:
        # 商务柱状图
        bar_colors = [COLOR_PRIMARY if i == len(values) - 1 else COLOR_SECONDARY for i in range(len(values))]
        bars = ax.bar(
            labels, values,
            color=bar_colors,
            width=0.48,
            edgecolor=COLOR_PRIMARY,
            linewidth=0.8,
            zorder=3
        )

        # 标注柱顶数值
        for bar, val, unit in zip(bars, values, units):
            height = bar.get_height()
            u = unit or primary_unit
            val_str = f"{int(val)}" if val.is_integer() else f"{val:.1f}"
            ax.annotate(
                f"{val_str}{u}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 6),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=10.5,
                fontweight="bold",
                color=COLOR_DARK,
                zorder=5
            )

    # 标题与副标题设置
    ax.set_title(title, fontsize=14, fontweight="bold", color=COLOR_DARK, pad=18, loc="left")

    # 坐标轴与栅格优化
    if x_label:
        ax.set_xlabel(x_label, fontsize=10.5, color=COLOR_MUTED, labelpad=8)
    if y_label:
        ax.set_ylabel(y_label, fontsize=10.5, color=COLOR_MUTED, labelpad=8)

    ax.tick_params(axis="x", labelsize=10, colors=COLOR_DARK)
    ax.tick_params(axis="y", labelsize=9.5, colors=COLOR_MUTED)

    # 仅保留水平细网格线，移除顶部与右侧外边框
    ax.yaxis.grid(True, linestyle="--", alpha=0.7, color=COLOR_GRID, zorder=0)
    ax.xaxis.grid(False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(COLOR_GRID)
    ax.spines["bottom"].set_color(COLOR_GRID)

    # Y 轴留白 15% 防止标签超出顶部
    y_min, y_max = ax.get_ylim()
    ax.set_ylim(min(0, y_min), y_max * 1.18 if y_max > 0 else 1)

    # 底部留存观察结论注解（如果存在）
    if takeaway:
        fig.text(
            0.12, 0.02, f"● 关键洞察: {takeaway}",
            fontsize=9.5, color=COLOR_MUTED, style="italic"
        )
        plt.subplots_adjust(bottom=0.18, top=0.88, left=0.12, right=0.92)
    else:
        plt.subplots_adjust(bottom=0.12, top=0.88, left=0.12, right=0.92)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(output_path), dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)

    print(f"📈 [图表引擎] 高清行业可视化图表已生成: {output_path}")
    return output_path
