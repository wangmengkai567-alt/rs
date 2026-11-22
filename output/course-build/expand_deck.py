from pathlib import Path
from shutil import copyfile

base = Path("output/course-build")
build = base / "expanded"
build.mkdir(exist_ok=True)
copyfile(base / "demo.png", build / "demo.png")
original = (base / "make_slides.mjs").read_text(encoding="utf-8")
text = original

def replace(old, new):
    global text
    assert text.count(old) == 1, old
    text = text.replace(old, new)

replace('path.join(root, "output", "course-build")', 'path.join(root, "output", "course-build", "expanded")')
replace('path.join(root, "课程提交")', 'path.join(root, "output", "course-build", "expanded-result")')
replace('Gowalla签到数据管理系统_课程汇报.pptx', 'Gowalla签到数据管理系统_课程汇报_9页.pptx')
replace('"presentation.validation.json"', '"presentation.final.validation.json"')
replace('建议用时 20 秒', '建议用时 15 秒')
replace('建议用时 45 秒\\n先看写入路径。', '建议用时 35 秒\\n先看写入路径。')
replace('建议用时 45 秒\\n实际读取到', '建议用时 35 秒\\n实际读取到')
replace('建议用时 50 秒', '建议用时 40 秒')
replace('建议用时 55 秒', '建议用时 35 秒')
replace('建议用时 45 秒\\n每类接口', '建议用时 35 秒\\n每类接口')

replace('s=slide("系统架构");', '''s=slide("课程任务与数据");
text(s,"Task","对全量签到完成清洗、双节点存储与查询验证",72,137,1135,55,
  {fontSize:"24pt",bold:true,color:de.green});
text(s,"Raw users","107,092",72,241,500,90,{fontSize:"52pt",color:de.dark,bold:true});
text(s,"Users label","原始数据中的用户数",74,342,467,43,{fontSize:"22pt",color:de.muted});
text(s,"Raw locations","1,280,969",632,241,536,90,{fontSize:"52pt",color:de.dark,bold:true});
text(s,"Locations label","原始数据中的地点数",635,342,470,43,{fontSize:"22pt",color:de.muted});
text(s,"Data columns title","每行 5 列",72,472,1100,43,{fontSize:"23pt",bold:true});
text(s,"Data columns","用户 ID、UTC 时间、纬度、经度、地点 ID",72,529,1110,48,
  {fontSize:"22pt",color:de.muted});
s.speakerNotes.text="建议用时 25 秒\\n任务书要求用全量附件验证清洗、至少两个数据节点上的存储和查询服务。Gowalla 原始数据覆盖约十万用户和一百二十八万个地点。每行给出用户、时间、纬度、经度和地点标识，这些字段支撑后面的轨迹与区域两类查询。\\n数据说明：https://snap.stanford.edu/data/loc-gowalla.html";

s=slide("系统架构");''')

old='''text(s,"Retry result caption","导入中断后重跑同一数据文件",72,501,1136,38,{fontSize:"21pt",bold:true,color:de.dark});
text(s,"Replay proof","匹配 1,190,000 条已有记录，新增 5,252,127 条。",72,552,1136,42,{fontSize:"19pt",color:de.muted});'''
replace(old, '''text(s,"Storage reconciliation","双分片合计与 6,442,127 条清洗通过记录一致",72,506,1136,52,
  {fontSize:"24pt",bold:true,color:de.dark});''')
replace('导入期间还中断过一次。从头重跑同一文件时，匹配了 119 万条已有记录，并继续写入剩余记录，最终没有多写。', '两个计数来自同一集合的独立节点读取，路由端统计和清洗通过条数也与两片合计一致。')
replace('s=slide("奥斯汀区域查询演示");', '''s=slide("导入中断后的重跑");
const replay=facts.import;
text(s,"Matched before restart",n(replay.already_present),72,197,512,83,
  {fontSize:"48pt",bold:true,color:de.dark});
text(s,"Matched label","匹配到中断前已写入的记录",73,293,517,45,
  {fontSize:"21pt",color:de.muted});
text(s,"New after restart",n(replay.inserted),636,197,527,83,
  {fontSize:"48pt",bold:true,color:de.green});
text(s,"Inserted label","本次重跑新增的记录",637,293,497,45,
  {fontSize:"21pt",color:de.muted});
text(s,"Identity mechanism","用户 ID 与源文件行号共同定位签到",72,426,1135,51,
  {fontSize:"25pt",bold:true,color:de.dark});
text(s,"Batch configuration","每批 5,000 条，最多并发提交四批。",72,497,1132,43,
  {fontSize:"20pt",color:de.muted});
s.speakerNotes.text="建议用时 30 秒\\n全量导入过程中实际中断了一次。重跑同一份文件，程序用完整分片键和源文件行号定位记录，匹配到 119 万条已经写入的签到，再插入剩余记录。最终计数仍与清洗输出相同，验证了中断后可以安全重跑。";

s=slide("用户轨迹与分页验证");
const trajectoryCounts=facts.verified.trajectory_counts;
const route=facts.verified.trajectory_query_shards[0];
table(s,"Verified trajectory counts",[
  ["用户 ID","完整签到条数"],["0",n(trajectoryCounts["0"])],["776",n(trajectoryCounts["776"])]
],72,178,624,231,[258,366],{fontSize:"23pt"});
text(s,"Page size","每页 71 条",757,192,430,53,{fontSize:"25pt",bold:true,color:de.green});
text(s,"Pagination evidence","翻完后核对总数、顺序和行号",757,264,447,43,{fontSize:"19pt"});
text(s,"Cursor rejection","跨用户复用游标返回 HTTP 422",757,318,449,42,{fontSize:"18pt",color:de.muted});
text(s,"Shard routing proof","用户 0 的执行计划只访问 "+route,72,496,1136,62,
  {fontSize:"27pt",bold:true,color:de.dark});
s.speakerNotes.text="建议用时 30 秒\\n轨迹接口按用户查签到。我们把每页设为七十一条，逐页读取用户零和用户七七六的完整记录，分别得到二百二十五条和两千一百七十四条。各页保持排序，没有重复源行号。用户零的执行计划只访问 shard1。";

s=slide("奥斯汀区域查询演示");''')
replace('"--require-native-table-slide","3","--require-native-table-slide","4","--require-native-table-slide","6"', '"--require-native-table-slide","4","--require-native-table-slide","5","--require-native-table-slide","7","--require-native-table-slide","9"')
replace('explicitTotalSlideCount:6,requiredNativeTableOwnerSlides:[3,4,6]', 'explicitTotalSlideCount:9,requiredNativeTableOwnerSlides:[4,5,7,9]')
(build / "make_slides.mjs").write_text(text,encoding="utf-8",newline="\n")
