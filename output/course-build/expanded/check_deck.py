from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET
import hashlib
import json
import re

base=Path("output/course-build")
build=base/"expanded"
stage=base/"expanded-result"/"presentation-final.pptx"
receipt=json.loads((build/"presentation.final.validation.json").read_text(encoding="utf-8"))
assert hashlib.sha256(stage.read_bytes()).hexdigest()==receipt["finalSha256"]
ns={"a":"http://schemas.openxmlformats.org/drawingml/2006/main"}
with ZipFile(stage) as ppt:
    assert ppt.testzip() is None
    slides=[k for k in ppt.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml",k)]
    assert len(slides)==9
    times=[]
    for i in range(1,10):
        note=ET.fromstring(ppt.read(f"ppt/notesSlides/notesSlide{i}.xml"))
        content="\n".join(n.text or "" for n in note.findall(".//a:t",ns))
        assert r"\n" not in content
        times.append(int(re.search(r"建议用时\s*(\d+)\s*秒",content).group(1)))
    assert times==[15,25,35,35,40,30,30,35,35] and sum(times)==280
    checks={2:["课程任务与数据","107,092","1,280,969"],5:["3,230,580","3,211,547","6,442,127"],
            6:["导入中断后的重跑","1,190,000","5,252,127"],
            7:["用户轨迹与分页验证","225","2,174","shard1"]}
    for i, expected in checks.items():
        slide=ET.fromstring(ppt.read(f"ppt/slides/slide{i}.xml"))
        strings="\n".join(n.text or "" for n in slide.findall(".//a:t",ns))
        assert all(value in strings for value in expected),(i,expected)
for old,new in [(1,1),(2,3),(3,4),(5,8),(6,9)]:
    assert (base/f"slide-{old}.png").read_bytes()==(build/f"slide-{new}.png").read_bytes(),(old,new)
print("Verified 9 slides, 280 seconds of notes, new evidence, and unchanged slides.")
