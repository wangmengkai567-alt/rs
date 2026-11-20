from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path.cwd()
source = [
    "README.md", ".gitignore", ".python-version", "compose.yaml", "pyproject.toml", "uv.lock",
    "社交媒体签到数据管理系统_实现方案.md",
    "output/acceptance.json", "output/quality_report.json", "output/preview.png",
]
for folder in ["api","cleaner","db","web"]:
    source.extend(
        file.relative_to(root).as_posix()
        for file in (root / folder).rglob("*")
        if file.is_file() and "__pycache__" not in file.parts
    )
assert len(source) == len(set(source))
archive = root / "课程提交" / "Gowalla签到数据管理系统_完整代码.zip"
with ZipFile(archive, "w", ZIP_DEFLATED, compresslevel=7) as dest:
    for name in sorted(source):
        dest.write(root / name, name)
with ZipFile(archive) as dest:
    assert dest.testzip() is None and set(dest.namelist()) == set(source)
print(f"Verified all {len(source)} ZIP entries")
