from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import FancyArrowPatch, Rectangle
from matplotlib.ticker import MultipleLocator, FuncFormatter

root = Path.cwd()
build = root / "output" / "course-build"
report = json.loads((root / "output" / "acceptance.json").read_text(encoding="utf-8"))
counts = report["import"]["shard_counts"]
assert sum(counts.values()) == report["quality"]["clean_count"]
song = FontProperties(fname="C:/Windows/Fonts/simsun.ttc")
latin = FontProperties(fname="C:/Windows/Fonts/times.ttf")
ink, label = "#173730", "#344b46"
shard1_blue, shard2_orange = "#195382", "#c77c17"

fig, ax = plt.subplots(figsize=(15.4/2.54, 5.9/2.54))
fig.subplots_adjust(left=0, right=1, bottom=0, top=1)
ax.set(xlim=(0, 10.2), ylim=(0, 4.0))
ax.axis("off")

def block(x, y, w, h, main, detail=None, *, kind="normal"):
    fills = {"normal": ("#eff5f1", "#a4bcb0"), "data": ("#dfeee9", "#519585"),
             "routing": ("#194d41", "#194d41")}
    fill, stroke = fills[kind]
    color = "#ffffff" if kind == "routing" else ink
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fill, edgecolor=stroke, linewidth=.75))
    ax.text(x+w/2, y+h*(.64 if detail else .5), main, ha="center", va="center",
            color=color, fontproperties=song, fontsize=8)
    if detail:
        ax.text(x+w/2, y+h*.30, detail, ha="center", va="center",
                color=color, fontproperties=song, fontsize=7.65)

def arrow(a, b, dashed=False):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=8,
                                color="#456f65", linewidth=.85,
                                linestyle="--" if dashed else "-",
                                shrinkA=0, shrinkB=0))

block(.15, 2.50, 1.65, .78, "Gowalla 文本", "课程数据")
block(2.18, 2.50, 1.65, .78, "流式清洗", "校验与去重")
block(4.22, 2.50, 1.65, .78, "批量导入", "PyMongo")
block(6.25, 2.50, 1.66, .78, "mongos", "分片路由", kind="routing")
block(8.45, 2.99, 1.54, .71, "shard1", "持久卷 1", kind="data")
block(8.45, 2.08, 1.54, .71, "shard2", "持久卷 2", kind="data")
block(2.18, 1.22, 1.65, .74, "拒收明细", "质量报告")
block(6.25, 1.22, 1.66, .74, "配置服务器", "分片元数据")
block(2.18, .12, 1.65, .74, "Leaflet 地图", "查询与展示")
block(4.22, .12, 1.65, .74, "FastAPI", "轨迹与范围")
for x1, x2 in [(1.80,2.18),(3.83,4.22),(5.87,6.25)]:
    arrow((x1,2.89), (x2,2.89))
arrow((7.91,2.97), (8.45,3.34))
arrow((7.91,2.79), (8.45,2.43))
arrow((3.00,2.50), (3.00,1.96))
arrow((7.08,2.50), (7.08,1.96), True)
arrow((3.83,.49), (4.22,.49))
ax.plot([5.87,8.12,8.12], [.49,.49,2.58], color="#456f65", linewidth=.85)
arrow((8.12,2.58),(7.91,2.58))
fig.savefig(build/"architecture.png", dpi=600, facecolor="white")
plt.close(fig)

fig, ax = plt.subplots(figsize=(15.4/2.54, 4.55/2.54))
fig.subplots_adjust(left=.15, right=.98, top=.91, bottom=.27)
total = sum(counts.values())
ax.barh([1,0], [counts["shard1"],counts["shard2"]], height=.43,
        color=[shard1_blue, shard2_orange], zorder=3)
ax.set_xlim(0, 4_950_000)
ax.set_ylim(-.52, 1.52)
ax.set_yticks([1,0], ["shard1","shard2"], fontproperties=latin, fontsize=8)
ax.xaxis.set_major_locator(MultipleLocator(1_000_000))
ax.xaxis.set_major_formatter(FuncFormatter(lambda val,pos: f"{val/10_000:.0f}"))
ax.tick_params(axis="x", labelsize=8, length=2.6, color="#7e918a", pad=3)
ax.tick_params(axis="y", length=0, pad=9)
for item in ax.get_xticklabels():
    item.set_fontproperties(latin)
    item.set_fontsize(8)
for value, y in zip(counts.values(), [1,0]):
    ax.text(value+73_000, y, f"{value:,}  ({value/total:.2%})",
            ha="left", va="center", color=ink, fontproperties=latin, fontsize=8.2)
ax.set_xlabel("签到记录数（万条）", fontproperties=song, fontsize=8, labelpad=3)
ax.spines[["left", "right", "top"]].set_visible(False)
ax.spines["bottom"].set_color("#93a29c")
ax.spines["bottom"].set_linewidth(.6)
ax.grid(axis="x", color="#d4ded9", linewidth=.55, zorder=0)
fig.savefig(build/"shards.png", dpi=600, facecolor="white")
plt.close(fig)
print("Rendered architecture and shard counts at 600 dpi")
