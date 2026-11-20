import re
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageOps, ImageDraw
from docx import Document
from pypdf import PdfReader

root=Path.cwd()
out=root/"课程提交"
build=root/"output"/"course-build"
docx=out/"Gowalla签到数据管理系统_实施报告.docx"
pptx=out/"Gowalla签到数据管理系统_课程汇报.pptx"
source=out/"Gowalla签到数据管理系统_完整代码.zip"

doc=Document(docx)
normal=[p.text for p in doc.paragraphs if p.style.name=="Normal"]
chars=len(re.findall(r"[\u3400-\u9fff]","".join(normal)))
assert chars==3411 and len(doc.inline_shapes)==3 and len(doc.tables)==4
ns={"w":"http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "a":"http://schemas.openxmlformats.org/drawingml/2006/main"}
with ZipFile(docx) as package:
    s=ET.fromstring(package.read("word/styles.xml"))
    title=s.find("w:style[@w:styleId='Title']",ns)
    assert title.find("w:pPr/w:pBdr",ns) is None
    normal=s.find("w:style[@w:styleId='Normal']",ns)
    assert normal.find("w:pPr/w:spacing",ns).get("{"+ns["w"]+"}line")=="320"
with ZipFile(pptx) as package:
    assert package.testzip() is None
    notes=sorted(name for name in package.namelist() if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml",name))
    assert len(notes)==6
    seconds=[]
    for name in notes:
        text="".join(n.text or "" for n in ET.fromstring(package.read(name)).findall(".//a:t",ns))
        seconds.append(int(re.search(r"建议用时\s*(\d+)\s*秒",text).group(1)))
    assert sum(seconds)==260
with ZipFile(source) as package:
    assert package.testzip() is None
    assert {"api/main.py","cleaner/pipeline.py","db/import_checkins.py","compose.yaml","uv.lock","output/acceptance.json"}.issubset(package.namelist())
    assert not any("clean.tsv" in name or ".pyc" in name or name.endswith(".gz") for name in package.namelist())
    assert len(package.namelist())==30

pdf=PdfReader(build/"doc-render"/"report.pdf")
assert len(pdf.pages)==6 and all(len(page.extract_text().strip())>270 for page in pdf.pages)
images=[Image.open(build/"doc-render"/f"page-{i}.png").convert("RGB") for i in range(1,7)]
canvas=Image.new("RGB",(1650,1578),"#e5e8e6")
for index, image in enumerate(images):
    image.thumbnail((522,760))
    canvas.paste(image, (10+(index%3)*550,10+(index//3)*788))
canvas.save(build/"report-review.png")
print("3411 Han body characters, 6 rendered pages, 3 figures, 4 tables")
print("6 slides, editable evidence tables, 260 seconds of planned speaker notes")
print("30 verified package entries")
