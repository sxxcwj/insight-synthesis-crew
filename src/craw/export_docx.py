import json
import re
from typing import Any, Optional
from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

from craw.export_charts import extract_chart_data_from_report, render_consulting_chart


def set_cell_background(cell, fill_hex):
    """设置单元格背景颜色"""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """设置单元格内边距 (单位：dxa, 20 dxa = 1 pt)"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('w:top', top), ('w:bottom', bottom), ('w:left', left), ('w:right', right)]:
        node = OxmlElement(m)
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def create_callout_box(doc, text, title="📋 执行摘要 (Executive Summary)"):
    """创建高亮引述卡片"""
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(6.5)

    cell = table.cell(0, 0)
    set_cell_background(cell, "F0F7FF")  # 柔和淡蓝底色
    set_cell_margins(cell, top=160, bottom=160, left=200, right=200)

    # 边框设置：仅左侧深蓝粗边框
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:top w:val="none"/>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="1D4ED8"/>'
        f'<w:bottom w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)

    p_title = cell.paragraphs[0]
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(4)
    run_t = p_title.add_run(title)
    run_t.font.name = "Microsoft YaHei"
    run_t.font.size = Pt(11)
    run_t.font.bold = True
    run_t.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)

    p_body = cell.add_paragraph()
    p_body.paragraph_format.space_before = Pt(2)
    p_body.paragraph_format.space_after = Pt(2)
    p_body.paragraph_format.line_spacing = 1.25
    run_b = p_body.add_run(text)
    run_b.font.name = "Microsoft YaHei"
    run_b.font.size = Pt(10)
    run_b.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)


def add_section_heading(doc, text, level=1):
    """添加带有精致样式的章节标题"""
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    
    if level == 1:
        p.paragraph_format.space_before = Pt(18)
        p.paragraph_format.space_after = Pt(6)
        run = p.add_run(text)
        run.font.name = "Microsoft YaHei"
        run.font.size = Pt(14)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)  # Slate 900
    elif level == 2:
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(text)
        run.font.name = "Microsoft YaHei"
        run.font.size = Pt(11.5)
        run.font.bold = True
        run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x8A)  # Navy Blue
    return p


def export_markdown_to_docx(md_or_data: Any, docx_path: Path, chart_image_path: Optional[Path] = None, auto_open: bool = True):
    """将生成的研究报告解析并导出为专业排版的 Word (.docx) 文档"""
    data = None
    if isinstance(md_or_data, dict):
        data = md_or_data
        content = ""
    else:
        content = Path(md_or_data).read_text(encoding="utf-8") if isinstance(md_or_data, (Path, str)) else ""

        # 尝试从文本中解析 JSON
        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                data = json.loads(json_match.group(0))
            except Exception:
                data = None

    # 若未找到 JSON，则通过 Markdown 结构智能解析为字典对象
    if not data and content:
        topic_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        topic_val = topic_match.group(1).strip() if topic_match else "研究课题简报"
        
        exec_match = re.search(r">\s*\*\*📋[^\*]+\*\*\s*\n+>\s*(.+?)(?=\n##|\Z)", content, re.DOTALL)
        exec_val = exec_match.group(1).strip().replace("\n> ", " ").replace("\n>", "") if exec_match else ""
        
        findings = []
        finding_matches = re.findall(r"###\s*1\.\d+\s*([^\n]+)\n+([\s\S]+?)(?=\n###|\n##|\Z)", content)
        for f_title, f_det in finding_matches:
            findings.append({"title": f_title.strip(), "details": f_det.strip()})
            
        risks = re.findall(r"\*\s*\*\*⚠️[^\*]+\*\*：?\s*([^\n]+)", content)
        
        recs = []
        rec_section = re.search(r"##\s*三[^\n]+\n+([\s\S]+?)(?=\n##|\Z)", content)
        if rec_section:
            recs = re.findall(r"^\d+\.\s*([^\n]+)", rec_section.group(1), re.MULTILINE)
            
        sources = []
        src_section = re.search(r"##\s*四[^\n]+\n+([\s\S]+?)(?=\n##|\Z)", content)
        if src_section:
            for s in re.findall(r"^\d+\.\s*\[([^\]]+)\]\(([^)]+)\)\s*(?:——|-)?\s*([^\n]*)", src_section.group(1), re.MULTILINE):
                sources.append({"title": s[0].strip(), "url": s[1].strip(), "evidence": s[2].strip()})

        data = {
            "topic": topic_val,
            "executive_summary": exec_val,
            "key_findings": findings,
            "risk_assessment": risks,
            "strategic_recommendations": recs,
            "sources": sources
        }

    # 尝试自动提取量化图表数据并生成高清图表
    if not chart_image_path:
        chart_info = extract_chart_data_from_report(data or md_or_data)
        if chart_info:
            c_path = docx_path.with_suffix(".png")
            try:
                render_consulting_chart(chart_info, c_path)
                chart_image_path = c_path
            except Exception as e:
                print(f"图表渲染提示: {e}")

    doc = Document()

    # 页面边距设置为 2.54 cm 标准
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    # 1. 主标题
    topic = data.get("topic") if data else "研究课题简报"
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(10)
    p_title.paragraph_format.space_after = Pt(4)
    run_title = p_title.add_run(topic)
    run_title.font.name = "Microsoft YaHei"
    run_title.font.size = Pt(18)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)

    # 副标题/元数据
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(18)
    run_sub = p_sub.add_run("DeepSeek-Flash 两阶段研究系统 | 深度交叉核验与决策简报")
    run_sub.font.name = "Microsoft YaHei"
    run_sub.font.size = Pt(9.5)
    run_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    # 如果成功提取到结构化数据
    if data:
        # 2. 执行摘要
        if "executive_summary" in data:
            create_callout_box(doc, data["executive_summary"])

        # 3. 核心洞察与发现
        if "key_findings" in data and data["key_findings"]:
            add_section_heading(doc, "一、 核心洞察与交叉核验发现 (Key Findings)", level=1)
            for idx, item in enumerate(data["key_findings"], 1):
                title = item.get("title", f"洞察 {idx}")
                details = item.get("details", "")
                
                add_section_heading(doc, f"1.{idx} {title}", level=2)
                p_desc = doc.add_paragraph()
                p_desc.paragraph_format.space_after = Pt(8)
                p_desc.paragraph_format.line_spacing = 1.25
                r_desc = p_desc.add_run(details)
                r_desc.font.name = "Microsoft YaHei"
                r_desc.font.size = Pt(10)
                r_desc.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

        has_chart = bool(chart_image_path and Path(chart_image_path).exists())

        # 4. 关键量化发展趋势图表 (若存在)
        if has_chart:
            add_section_heading(doc, "二、 关键量化发展趋势研判 (Quantitative Market Overview)", level=1)
            p_img = doc.add_paragraph()
            p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_img.paragraph_format.space_before = Pt(8)
            p_img.paragraph_format.space_after = Pt(4)
            r_img = p_img.add_run()
            r_img.add_picture(str(chart_image_path), width=Inches(6.2))

            p_cap = doc.add_paragraph()
            p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_cap.paragraph_format.space_after = Pt(14)
            r_cap = p_cap.add_run("图 1：行业关键量化指标与发展趋势研判 (数据来源：研报综合测算与多源交叉核验)")
            r_cap.font.name = "Microsoft YaHei"
            r_cap.font.size = Pt(8.5)
            r_cap.font.italic = True
            r_cap.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

        sec_num_risk = "三" if has_chart else "二"
        sec_num_rec = "四" if has_chart else "三"
        sec_num_src = "五" if has_chart else "四"

        # 5. 风险与不确定性评估
        if "risk_assessment" in data and data["risk_assessment"]:
            add_section_heading(doc, f"{sec_num_risk}、 潜在风险与不确定性研判 (Risk Assessment)", level=1)
            for idx, risk_text in enumerate(data["risk_assessment"], 1):
                p_risk = doc.add_paragraph()
                p_risk.paragraph_format.space_after = Pt(6)
                p_risk.paragraph_format.line_spacing = 1.25
                
                # 分离标题与正文（如果含有冒号或竖线）
                r_num = p_risk.add_run(f"• 风险点 {idx}：")
                r_num.font.name = "Microsoft YaHei"
                r_num.font.bold = True
                r_num.font.size = Pt(10)
                r_num.font.color.rgb = RGBColor(0xB9, 0x1C, 0x1C)  # 深红警戒色

                r_body = p_risk.add_run(risk_text)
                r_body.font.name = "Microsoft YaHei"
                r_body.font.size = Pt(10)
                r_body.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

        # 6. 战略行动建议
        if "strategic_recommendations" in data and data["strategic_recommendations"]:
            add_section_heading(doc, f"{sec_num_rec}、 前瞻性战略行动建议 (Strategic Recommendations)", level=1)
            for idx, rec in enumerate(data["strategic_recommendations"], 1):
                p_rec = doc.add_paragraph()
                p_rec.paragraph_format.space_after = Pt(6)
                p_rec.paragraph_format.line_spacing = 1.25

                r_num = p_rec.add_run(f"{idx}. ")
                r_num.font.name = "Microsoft YaHei"
                r_num.font.bold = True
                r_num.font.size = Pt(10)
                r_num.font.color.rgb = RGBColor(0x04, 0x78, 0x57)  # 深绿决策建议色

                r_body = p_rec.add_run(rec)
                r_body.font.name = "Microsoft YaHei"
                r_body.font.size = Pt(10)
                r_body.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

        # 7. 权威引用与信息来源清单 (References & Sources)
        sources_list = data.get("sources") or data.get("references") or []
        if sources_list:
            add_section_heading(doc, f"{sec_num_src}、 权威引用与信息来源清单 (References & Sources)", level=1)
            
            # 创建精美参考文献表格
            table = doc.add_table(rows=1, cols=4)
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            table.autofit = False
            
            col_widths = [Inches(0.6), Inches(2.0), Inches(2.2), Inches(1.7)]
            for col_idx, width in enumerate(col_widths):
                table.columns[col_idx].width = width

            # 表头
            hdr_cells = table.rows[0].cells
            headers = ["序号", "来源机构 / 文献标题", "核心论据与支撑事实", "引用链接 (URL)"]
            for i, text in enumerate(headers):
                hdr_cells[i].width = col_widths[i]
                set_cell_background(hdr_cells[i], "1E3A8A")  # 深蓝表头
                set_cell_margins(hdr_cells[i], top=120, bottom=120, left=120, right=120)
                p = hdr_cells[i].paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                run = p.add_run(text)
                run.font.name = "Microsoft YaHei"
                run.font.size = Pt(9.5)
                run.font.bold = True
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

            # 数据行
            for idx, src in enumerate(sources_list, 1):
                row_cells = table.add_row().cells
                for i, w in enumerate(col_widths):
                    row_cells[i].width = w
                    bg_color = "F8FAFC" if idx % 2 == 0 else "FFFFFF"
                    set_cell_background(row_cells[i], bg_color)
                    set_cell_margins(row_cells[i], top=100, bottom=100, left=100, right=100)

                # 序号
                p0 = row_cells[0].paragraphs[0]
                p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r0 = p0.add_run(str(idx))
                r0.font.name = "Microsoft YaHei"
                r0.font.size = Pt(9)
                r0.font.bold = True

                # 机构/标题
                p1 = row_cells[1].paragraphs[0]
                title = src.get("title", "") if isinstance(src, dict) else str(src)
                r1 = p1.add_run(title)
                r1.font.name = "Microsoft YaHei"
                r1.font.size = Pt(9)
                r1.font.bold = True
                r1.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)

                # 证据点
                p2 = row_cells[2].paragraphs[0]
                p2.paragraph_format.line_spacing = 1.15
                evidence = src.get("evidence", "") if isinstance(src, dict) else ""
                r2 = p2.add_run(evidence)
                r2.font.name = "Microsoft YaHei"
                r2.font.size = Pt(8.5)
                r2.font.color.rgb = RGBColor(0x47, 0x55, 0x69)

                # 链接 URL
                p3 = row_cells[3].paragraphs[0]
                url = src.get("url", "") if isinstance(src, dict) else ""
                r3 = p3.add_run(url)
                r3.font.name = "Calibri"
                r3.font.size = Pt(8.5)
                r3.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
                r3.font.underline = True

            doc.add_paragraph().paragraph_format.space_after = Pt(12)

    else:
        # 降级：作为普通文本渲染
        p = doc.add_paragraph(content)
        p.paragraph_format.line_spacing = 1.25

    docx_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(docx_path))
    print(f"✅ 专业 Word 文档已成功生成: {docx_path}")

    # 将配套 Markdown 同步重构为排版优雅的人类可读 Markdown（消除 JSON 乱码感）
    if data:
        try:
            formatted_md = []
            formatted_md.append(f"# {topic}\n")
            if "executive_summary" in data:
                formatted_md.append(f"> **📋 执行摘要 (Executive Summary)**\n>\n> {data['executive_summary']}\n")
            
            if "key_findings" in data and data["key_findings"]:
                formatted_md.append("## 一、 核心洞察与交叉核验发现 (Key Findings)\n")
                for idx, item in enumerate(data["key_findings"], 1):
                    formatted_md.append(f"### 1.{idx} {item.get('title', '')}\n")
                    formatted_md.append(f"{item.get('details', '')}\n")

            if has_chart:
                chart_rel_name = Path(chart_image_path).name
                formatted_md.append("## 二、 关键量化发展趋势研判 (Quantitative Market Overview)\n")
                formatted_md.append(f"![行业关键量化发展趋势研判]({chart_rel_name})\n\n")
            
            if "risk_assessment" in data and data["risk_assessment"]:
                formatted_md.append(f"## {sec_num_risk}、 潜在风险与不确定性研判 (Risk Assessment)\n")
                for idx, risk_text in enumerate(data["risk_assessment"], 1):
                    formatted_md.append(f"* **⚠️ 风险点 {idx}**：{risk_text}\n")
            
            if "strategic_recommendations" in data and data["strategic_recommendations"]:
                formatted_md.append(f"## {sec_num_rec}、 前瞻性战略行动建议 (Strategic Recommendations)\n")
                for idx, rec in enumerate(data["strategic_recommendations"], 1):
                    formatted_md.append(f"{idx}. {rec}\n")

            if sources_list:
                formatted_md.append(f"## {sec_num_src}、 权威引用与信息来源清单 (References & Sources)\n")
                for idx, src in enumerate(sources_list, 1):
                    if isinstance(src, dict):
                        stitle = src.get('title', '参考来源')
                        surl = src.get('url', '')
                        sevidence = src.get('evidence', '')
                        link_part = f"[{stitle}]({surl})" if surl else f"**{stitle}**"
                        desc_part = f" —— {sevidence}" if sevidence else ""
                        formatted_md.append(f"{idx}. {link_part}{desc_part}\n")
                    else:
                        formatted_md.append(f"{idx}. {src}\n")
            
            target_md_path = (
                Path(md_or_data)
                if isinstance(md_or_data, (Path, str)) and Path(md_or_data).suffix == ".md"
                else docx_path.with_suffix(".md")
            )
            target_md_path.write_text("\n".join(formatted_md), encoding="utf-8")
        except Exception:
            pass

    # 自动唤起系统 Word 应用打开文档，无需用户手动输入命令
    import platform
    import subprocess
    if auto_open and platform.system() == "Darwin":
        try:
            # 优先尝试使用 Microsoft Word 打开，若无则使用默认应用打开
            res = subprocess.run(["open", "-a", "Microsoft Word", str(docx_path)], check=False, capture_output=True)
            if res.returncode != 0:
                subprocess.run(["open", str(docx_path)], check=False)
            print(f"🚀 已自动调用 Microsoft Word 为您打开该文档！")
        except Exception as e:
            print(f"提示: 自动打开 Word 失败: {e}")

    return docx_path


def get_report_paths(output_dir_or_topic: Any = Path("reports"), topic: str = None):
    """
    为每次研究生成带时间戳的历史归档文件保存在 reports/archive/ 目录下，
    同时在 reports/ 根目录下维护一份 latest (research_report.*) 最新副本。
    涵盖 Markdown (.md)、Word (.docx) 以及 PowerPoint (.pptx)。
    支持 get_report_paths(output_dir, topic) 或 get_report_paths(topic)。
    """
    import datetime
    if topic is None:
        if isinstance(output_dir_or_topic, (str, Path)) and not Path(output_dir_or_topic).is_dir():
            topic = str(output_dir_or_topic)
            output_dir = Path("reports")
        else:
            output_dir = Path(output_dir_or_topic)
            topic = "research_report"
    else:
        output_dir = Path(output_dir_or_topic)

    output_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = output_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    clean_topic = re.sub(r'[\\/*?:"<>| \t\n]', '_', str(topic))[:25].strip('_')
    if not clean_topic:
        clean_topic = "research_report"

    archive_md = archive_dir / f"{now_str}_{clean_topic}.md"
    archive_docx = archive_dir / f"{now_str}_{clean_topic}.docx"
    archive_pptx = archive_dir / f"{now_str}_{clean_topic}.pptx"
    latest_md = output_dir / "research_report.md"
    latest_docx = output_dir / "research_report.docx"
    latest_pptx = output_dir / "research_report.pptx"

    return archive_md, archive_docx, archive_pptx, latest_md, latest_docx, latest_pptx


if __name__ == "__main__":
    report_md = Path("reports/research_report.md")
    report_docx = Path("reports/research_report.docx")
    if report_md.exists():
        export_markdown_to_docx(report_md, report_docx)
    else:
        print("未找到 reports/research_report.md 文件")

