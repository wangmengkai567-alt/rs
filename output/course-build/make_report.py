from pathlib import Path
import json
import re

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from docx.opc.constants import RELATIONSHIP_TYPE

root = Path.cwd()
build = root / "output" / "course-build"
output = root / "课程提交"
output.mkdir(exist_ok=True)
pages = json.loads((build / "report-content.json").read_text(encoding="utf-8"))

doc = Document()
doc.core_properties.title = "基于双分片的 Gowalla 签到数据管理系统"
doc.core_properties.subject = "测绘遥感工程实施案例设计实施报告"
doc.core_properties.author = "课程项目组"

section = doc.sections[0]
section.page_width = Cm(21)
section.page_height = Cm(29.7)
section.left_margin = section.right_margin = Cm(2.8)
section.top_margin = Cm(2.2)
section.bottom_margin = Cm(2.05)
section.footer_distance = Cm(1.0)

def el(parent, tag, **attrs):
    element = OxmlElement(f"w:{tag}")
    for key, value in attrs.items():
        element.set(qn(f"w:{key}"), str(value))
    parent.append(element)
    return element

def style_font(style, size, east="宋体", bold=False):
    style.font.name = "Times New Roman"
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    fonts = style.element.get_or_add_rPr().rFonts
    fonts.set(qn("w:eastAsia"), east)
    fonts.set(qn("w:cs"), "Times New Roman")
    for name in ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme"):
        fonts.attrib.pop(qn("w:" + name), None)

def add_style(name, size, *, east="宋体", align=WD_ALIGN_PARAGRAPH.LEFT,
              spacing=16, before=0, after=0, keep=False):
    style = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    style.base_style = doc.styles["Normal"]
    style_font(style, size, east)
    configure(style, align, spacing, before, after, keep)
    return style

def configure(style, align, spacing, before, after, keep):
    p = style.paragraph_format
    p.alignment = align
    p.line_spacing = Pt(spacing) if isinstance(spacing, int) else spacing
    p.space_before = Pt(before)
    p.space_after = Pt(after)
    p.keep_with_next = keep
    p.widow_control = True

normal = doc.styles["Normal"]
style_font(normal, 10.5)
configure(normal, WD_ALIGN_PARAGRAPH.JUSTIFY, 16, 0, 0, False)
style_font(doc.styles["Title"], 12, "黑体")
title_style = doc.styles["Title"]
configure(title_style, WD_ALIGN_PARAGRAPH.CENTER, 1.5, 0, 6, True)
title_properties = title_style.element.get_or_add_pPr()
for border in title_properties.findall(qn("w:pBdr")):
    title_properties.remove(border)
for level in [1, 2]:
    style = doc.styles[f"Heading {level}"]
    style_font(style, 12, "黑体")
    configure(style, WD_ALIGN_PARAGRAPH.LEFT, 1.0, 6, 6, True)

roster = add_style("Member List", 10.5, align=WD_ALIGN_PARAGRAPH.CENTER,
                   spacing=1.5, keep=True)
titlecap = add_style("Caption Chinese", 7.5, align=WD_ALIGN_PARAGRAPH.CENTER,
                     spacing=11, before=3, keep=True)
engcap = add_style("Caption English", 7.5, align=WD_ALIGN_PARAGRAPH.CENTER,
                   spacing=10, after=3)
picture = add_style("Figure Artwork", 8, align=WD_ALIGN_PARAGRAPH.CENTER,
                    spacing=1.0, before=5, keep=True)
cell_text = add_style("Three Line Table", 9, spacing=13)
reference = add_style("Reference Entry", 8.5, spacing=12, before=0, after=0)
footer_style = add_style("Page Number", 8, align=WD_ALIGN_PARAGRAPH.CENTER, spacing=12)

def paragraph(text):
    p = doc.add_paragraph(text)
    el(p._p.get_or_add_pPr(), "ind", firstLineChars=200)
    return p

def link(paragraph, url):
    rel_id = paragraph.part.relate_to(url, RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = el(paragraph._p, "hyperlink")
    hyperlink.set(qn("r:id"), rel_id)
    run = el(hyperlink, "r")
    props = el(run, "rPr")
    el(props, "rFonts", ascii="Times New Roman", hAnsi="Times New Roman", eastAsia="宋体")
    el(props, "color", val="000000")
    el(props, "sz", val=17)
    el(run, "t").text = url

def figure(filename, width, cn, en):
    p = doc.add_paragraph(style=picture)
    p.add_run().add_picture(str(build / filename), width=Cm(width))
    doc.add_paragraph(cn, style=titlecap)
    doc.add_paragraph(en, style=engcap)

def three_line_table(caption, english, rows, widths, numeric):
    doc.add_paragraph(caption, style=titlecap)
    p = doc.add_paragraph(english, style=engcap)
    p.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=len(rows), cols=len(widths))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    pr = t._tbl.tblPr
    borders = el(pr, "tblBorders")
    for side in ("top","left","bottom","right","insideH","insideV"):
        el(borders, side, val="single" if side in ("top","bottom") else "nil",
           sz=9 if side in ("top","bottom") else 0, color="000000")
    mar = el(pr, "tblCellMar")
    for side in ("top", "bottom", "left", "right"):
        el(mar, side, w=28 if side in ("top","bottom") else 95, type="dxa")
    for i, width in enumerate(widths):
        t.columns[i].width = Cm(width)
    for index, values in enumerate(rows):
        row = t.rows[index]
        tr = row._tr.get_or_add_trPr()
        el(tr, "cantSplit")
        if index == 0:
            el(tr, "tblHeader", val="true")
        for i, value in enumerate(values):
            cell = row.cells[i]
            cell.width = Cm(widths[i])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = cell.paragraphs[0]
            p.style = cell_text
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if i in numeric else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.keep_with_next = index < len(rows) - 1
            run = p.add_run(value)
            if index == 0:
                run.bold = True
                el(el(cell._tc.get_or_add_tcPr(), "tcBorders"), "bottom",
                   val="single", sz=5, color="000000")
    after = doc.add_paragraph(style=engcap)
    after.paragraph_format.line_spacing = Pt(3)
    after.paragraph_format.space_after = Pt(2)

doc.add_paragraph(doc.core_properties.title, style="Title")
doc.add_paragraph("组长　学号____________ 姓名________　　组员　学号____________ 姓名________", style=roster)
doc.add_paragraph("学号____________ 姓名________　　学号____________ 姓名________", style=roster)
doc.add_paragraph("学号____________ 姓名________　　学号____________ 姓名________", style=roster)

for page_idx, page in enumerate(pages):
    for i, row in enumerate(page):
        kind, *value = row
        if kind in ("h", "h2"):
            p = doc.add_paragraph(value[0], style="Heading 1" if kind == "h" else "Heading 2")
            if page_idx and i == 0:
                p.paragraph_format.page_break_before = True
        elif kind == "p":
            paragraph(value[0])
        elif kind == "fig":
            figure(*value)
        elif kind == "table":
            three_line_table(*value)
        elif kind == "refs":
            doc.add_paragraph(value[0], style="Heading 1")
            for number, (entry, url, *english) in enumerate(value[1], 1):
                p = doc.add_paragraph(f"[{number}] {entry}", style=reference)
                p.paragraph_format.keep_together = True
                if english:
                    p.add_run(" (" + english[0] + ")")
                if url:
                    p.add_run(" ")
                    link(p, url)
        else:
            raise ValueError(kind)

footer = section.footer.paragraphs[0]
footer.style = footer_style
el(footer._p, "fldSimple", instr="PAGE")
body = "".join(row[1] for page in pages for row in page if row[0] == "p")
han_count = len(re.findall(r"[\u3400-\u9fff]", body))
assert han_count >= 3000
target = output / "Gowalla签到数据管理系统_实施报告.docx"
doc.save(target)
print(f"Saved {target.name} with {han_count} Chinese characters in the report body")
