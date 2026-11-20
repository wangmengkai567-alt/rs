import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Presentation, PresentationFile } from "@oai/artifact-tool";

const root = process.cwd();
const build = path.join(root, "output", "course-build", "expanded");
const destination = path.join(root, "output", "course-build", "expanded-result");
const skill = "C:/Users/Dell/.codex/plugins/cache/openai-primary-runtime/presentations/26.1118.11504/skills/presentations";
const python = "C:/Users/Dell/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe";
const facts = JSON.parse(await fs.readFile(path.join(root, "output", "acceptance.json"), "utf8"));
const q = facts.quality;
const n = x => x.toLocaleString("en-US");
const pct = x => (100*x/q.clean_count).toFixed(2) + "%";
const de = {
  paper:"#F5F7F3", white:"#FFFFFF", dark:"#173A35", text:"#182D29", muted:"#4C635A",
  green:"#1A6B5B", soft:"#E7F1EB", border:"#D1DED6", mint:"#BCE2CC",
};
const font = "Microsoft YaHei";
const W=1280, H=720;
const deck = Presentation.create({slideSize:{width:W,height:H}});
const none = {fill:"none", width:0, style:"solid"};

function text(slide, name, value, x, y, w, h, style={}) {
  const item=slide.shapes.add({name, geometry:"textbox",
    position:{left:x,top:y,width:w,height:h}, fill:"none", line:none});
  item.text=value;
  item.text.style={
    typeface:font, fontSize:"20pt", color:de.text, insets:0, wrap:"none",
    verticalAlignment:"middle", ...style
  };
  return item;
}

function slide(title) {
  const item=deck.slides.add();
  item.background.fill=de.paper;
  if(title) text(item,"Slide title",title,72,58,1136,66,{fontSize:"36pt",bold:true,color:de.dark});
  return item;
}

function box(item,name,main,detail,x,y,w,h,fill=de.white){
  const frame=item.shapes.add({name,geometry:"rect",position:{left:x,top:y,width:w,height:h},
    fill,line:{style:"solid",fill:de.border,width:1.6}});
  const foreground=fill===de.dark?de.white:de.dark;
  text(item,name+" name",main,x+10,y+16,w-20,38,{fontSize:"20pt",bold:true,alignment:"center",color:foreground});
  text(item,name+" detail",detail,x+8,y+60,w-16,30,{fontSize:"13pt",alignment:"center",color:fill===de.dark?de.mint:de.muted});
  return frame;
}

function arrow(item,name,x,y,w=35){
  item.shapes.add({name,geometry:"rightArrow",position:{left:x,top:y,width:w,height:15},
    fill:de.green,line:none});
}

function table(item,name,rows,x,y,width,height,widths, options={}){
  const t=item.tables.add({rows:rows.length,columns:rows[0].length,left:x,top:y,width,height,
    columnWidths:widths,values:rows});
  t.styleOptions={headerRow:false,bandedRows:false,firstColumn:false};
  t.borders.assign({style:"solid",fill:de.border,width:1});
  for (let r=0;r<rows.length;r++){
    t.rows[r].height=height/rows.length;
    for(let c=0;c<rows[0].length;c++){
      const cell=t.getCell(r,c);
      cell.fill=r===0?de.dark:(r%2===0?de.soft:de.white);
      cell.text.style={
        typeface:font,fontSize:options.fontSize||"20pt",bold:r===0,
        color:r===0?de.white:de.text,alignment:c===0?"left":"center",verticalAlignment:"middle",
        insets:{left:13,right:13,top:6,bottom:6},
      };
    }
  }
  return t;
}

let s=slide();
s.background.fill=de.dark;
text(s,"Course title","测绘遥感工程实施案例",78,101,1115,40,{fontSize:"22pt",color:de.mint});
text(s,"Presentation title line one","Gowalla 签到数据",76,169,1124,88,{fontSize:"56pt",bold:true,color:de.white});
text(s,"Presentation title line two","双分片管理系统",76,256,1124,88,{fontSize:"56pt",bold:true,color:de.white});
text(s,"Project scope","清洗、分布存储与地图查询的全量验证",80,399,1110,53,{fontSize:"25pt",color:de.mint});
text(s,"Team","组长  __________     组员  ____________________________________",80,559,1120,42,
  {fontSize:"17pt",color:de.white});
s.speakerNotes.text="建议用时 15 秒\n大家好。本次案例针对课程下发的 Gowalla 签到数据，实现数据清洗、两节点分布式存储和地图查询。我们用完整附件跑了一遍，从原始行数一直核对到数据库和查询结果。\n依据：课程任务书《测绘遥感工程实施案例（2026—2027 第1学期）》";

s=slide("课程任务与数据");
text(s,"Task","对全量签到完成清洗、双节点存储与查询验证",72,137,1135,55,
  {fontSize:"24pt",bold:true,color:de.green});
text(s,"Raw users","107,092",72,241,500,90,{fontSize:"52pt",color:de.dark,bold:true});
text(s,"Users label","原始数据中的用户数",74,342,467,43,{fontSize:"22pt",color:de.muted});
text(s,"Raw locations","1,280,969",632,241,536,90,{fontSize:"52pt",color:de.dark,bold:true});
text(s,"Locations label","原始数据中的地点数",635,342,470,43,{fontSize:"22pt",color:de.muted});
text(s,"Data columns title","每行 5 列",72,472,1100,43,{fontSize:"23pt",bold:true});
text(s,"Data columns","用户 ID、UTC 时间、纬度、经度、地点 ID",72,529,1110,48,
  {fontSize:"22pt",color:de.muted});
s.speakerNotes.text="建议用时 25 秒\n任务书要求用全量附件验证清洗、至少两个数据节点上的存储和查询服务。Gowalla 原始数据覆盖约十万用户和一百二十八万个地点。每行给出用户、时间、纬度、经度和地点标识，这些字段支撑后面的轨迹与区域两类查询。\n数据说明：https://snap.stanford.edu/data/loc-gowalla.html";

s=slide("系统架构");
text(s,"Database technology","MongoDB 7.0 负责分片存储，FastAPI 提供查询",72,134,1130,43,{fontSize:"21pt",color:de.muted});
box(s,"Course data","Gowalla 文件","用户、时间、地点",72,232,195,108);
box(s,"Cleaner","流式清洗","校验、隔离、去重",317,232,195,108,de.soft);
box(s,"Router","mongos","路由写入和查询",562,232,195,108,de.dark);
box(s,"First shard","shard1","独立数据卷",842,175,199,108);
box(s,"Second shard","shard2","独立数据卷",842,302,199,108);
arrow(s,"Source to cleaner",275,279,36);
arrow(s,"Cleaner to router",521,279,34);
s.shapes.add({name:"Branch stem",geometry:"rect",position:{left:756,top:285,width:25,height:3},fill:de.green,line:none});
s.shapes.add({name:"Branch trunk",geometry:"rect",position:{left:779,top:229,width:3,height:127},fill:de.green,line:none});
arrow(s,"Router to first shard",780,222,55);
arrow(s,"Router to second shard",780,347,55);
text(s,"Shard qualifier","用户 ID 哈希分片",842,418,330,36,{fontSize:"17pt",color:de.green,bold:true});
text(s,"Import label","PyMongo 批量导入",454,358,330,33,{fontSize:"15pt",color:de.muted});
text(s,"Read path","地图页面经 FastAPI 与 mongos 查询签到",72,502,1136,47,{fontSize:"24pt",bold:true});
text(s,"Metadata service","配置服务器保存集群分片元数据，两个数据节点使用独立持久卷。",72,563,1136,45,{fontSize:"19pt",color:de.muted});
s.speakerNotes.text="建议用时 35 秒\n先看写入路径。清洗程序按用户组读取文本并留下质量记录，PyMongo 把通过的签到批量交给 Mongos。Mongos 根据用户哈希键把记录路由到两个数据分片。配置服务器维护分片元数据，两个分片各用独立持久卷。查询从地图页面进入 FastAPI，再通过同一个路由。带用户等值条件的轨迹查询可以定向到一个分片，区域查询需要两片共同参与。\n参考：https://www.mongodb.com/docs/v7.0/core/hashed-sharding/";

s=slide("全量清洗与对账");
text(s,"Raw label","附件实读",72,166,430,36,{fontSize:"20pt",color:de.muted});
text(s,"Raw number",n(q.input_count),72,205,460,87,{fontSize:"48pt",bold:true});
text(s,"Clean label","清洗通过",633,166,475,36,{fontSize:"20pt",color:de.muted});
text(s,"Clean number",n(q.clean_count),633,205,540,87,{fontSize:"48pt",bold:true,color:de.green});
table(s,"Rejection reason counts",[
  ["拒收原因","条数"],["坐标越界",n(q.reason_counts.BAD_COORD)],["经纬度同时为零",n(q.reason_counts.ZERO_COORD)],
  ["重复签到",n(q.reason_counts.DUPLICATE)],["合计",n(q.reject_count)]],
  72,327,678,274,[465,213],{fontSize:"18pt"});
text(s,"File count difference","附件比任务书标注多 2 条。",789,365,413,42,{fontSize:"19pt",color:de.dark});
text(s,"Traceability note","拒收记录保留源文件行号。",789,460,413,38,{fontSize:"18pt",color:de.muted});
text(s,"Traceability note two","同一条记录只计一个原因。",789,510,413,38,{fontSize:"18pt",color:de.muted});
s.speakerNotes.text="建议用时 35 秒\n实际读取到 644 万余条记录，比任务书标注多两条。我们核对了压缩包与解压文本的一致性，采用实读记录数对账。逐条检查字段、时间和坐标后，再按用户、时间、地点与坐标一起去重。最终拒收 765 条，其中重复 601 条、双零坐标 135 条、越界 29 条。拒收明细可以通过源行号回查，清洗后的 6,442,127 条就是入库验收的基准。\n数据来源：https://snap.stanford.edu/data/loc-gowalla.html";

s=slide("两个分片的全量验收");
const a=facts.import.shard_counts.shard1, b=facts.import.shard_counts.shard2;
table(s,"Direct shard counts",[
  ["数据分片","记录数","占比"],["shard1",n(a),pct(a)],["shard2",n(b),pct(b)],
  ["合计",n(a+b),"100.00%"]
],72,175,708,278,[233,244,231],{fontSize:"21pt"});
text(s,"Direct audit","直连两个分片计数",832,183,370,47,{fontSize:"23pt",bold:true});
text(s,"Router reconciliation","两片合计与路由计数一致",832,247,386,40,{fontSize:"18pt",color:de.muted});
text(s,"Orphans","孤立文档数为 0",832,308,370,36,{fontSize:"18pt",color:de.muted});
text(s,"Storage reconciliation","双分片合计与 6,442,127 条清洗通过记录一致",72,506,1136,52,
  {fontSize:"24pt",bold:true,color:de.dark});
s.speakerNotes.text="建议用时 40 秒\n我们通过路由统计集合总数，查看每片持有文档和孤立文档，再直连两个数据分片分别数记录。表中的两个分片实际持有约 323 万和 321 万条，合计与清洗输出相等。两个计数来自同一集合的独立节点读取，路由端统计和清洗通过条数也与两片合计一致。\n方法参考：https://www.mongodb.com/docs/v7.0/reference/operator/aggregation/shardeddatadistribution/";

s=slide("导入中断后的重跑");
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
s.speakerNotes.text="建议用时 30 秒\n全量导入过程中实际中断了一次。重跑同一份文件，程序用完整分片键和源文件行号定位记录，匹配到 119 万条已经写入的签到，再插入剩余记录。最终计数仍与清洗输出相同，验证了中断后可以安全重跑。";

s=slide("用户轨迹与分页验证");
const trajectoryCounts=facts.verified.trajectory_counts;
const route=facts.plans.trajectory.queryPlanner.winningPlan.shards[0].shardName;
table(s,"Verified trajectory counts",[
  ["用户 ID","完整签到条数"],["0",n(trajectoryCounts["0"])],["776",n(trajectoryCounts["776"])]
],72,178,624,231,[258,366],{fontSize:"23pt"});
text(s,"Page size","每页 71 条",757,192,430,53,{fontSize:"25pt",bold:true,color:de.green});
text(s,"Pagination evidence","翻完后核对总数、顺序和行号",757,264,447,43,{fontSize:"19pt"});
text(s,"Cursor rejection","跨用户复用游标返回 HTTP 422",757,318,449,42,{fontSize:"18pt",color:de.muted});
text(s,"Shard routing proof","用户 0 的执行计划只访问 "+route,72,496,1136,62,
  {fontSize:"27pt",bold:true,color:de.dark});
s.speakerNotes.text="建议用时 30 秒\n轨迹接口按用户查签到。我们把每页设为七十一条，逐页读取用户零和用户七七六的完整记录，分别得到二百二十五条和两千一百七十四条。各页保持排序，没有重复源行号。用户零的执行计划只访问 shard1。";

s=slide("奥斯汀区域查询演示");
text(s,"Austin query bounds","奥斯汀城市范围",72,185,325,46,{fontSize:"24pt",bold:true});
text(s,"Selected period","1 秒 UTC 时间窗",72,249,325,42,{fontSize:"20pt",color:de.muted});
text(s,"Source row evidence","源文件第 1 行",72,356,326,57,{fontSize:"28pt",bold:true,color:de.green});
text(s,"User ID","用户 ID  0",72,429,325,44,{fontSize:"20pt"});
text(s,"POI ID","地点 ID  22847",72,481,325,44,{fontSize:"20pt"});
const demo = new Uint8Array(await fs.readFile(path.join(build,"demo.png")));
s.images.add({name:"Austin query screenshot",blob:demo,contentType:"image/png",
  position:{left:432,top:151,width:778,height:502.5},fit:"contain"});
s.speakerNotes.text="建议用时 35 秒\n左边是这一例的核对重点，右边是本机系统运行时的截图。选取奥斯汀城区的一个范围，时间限制在 2010 年 10 月 19 日 23 点 55 分 27 秒开始的一秒。指一下图中选框里的签到点和底部列表。返回的是源文件第 1 行，用户 0，地点 22847。地图标记和结果列表指向同一条原始记录。区域查询的执行计划显示，两片共同参与这一请求。\n截图源于课程系统的实时请求，底图 © OpenStreetMap contributors。";

s=slide("查询性能与结论");
const track=facts.performance.trajectory, region=facts.performance.region;
table(s,"Measured end-to-end latency",[
  ["查询","访问分片","P50","P95","失败请求"],
  ["用户轨迹","1",track.p50_ms.toFixed(1)+" ms",track.p95_ms.toFixed(1)+" ms","0 / 100"],
  ["区域签到","2",region.p50_ms.toFixed(1)+" ms",region.p95_ms.toFixed(1)+" ms","0 / 100"]
],72,174,1129,235,[244,210,208,224,243],{fontSize:"21pt"});
text(s,"Measurement scope","本机预热后测量 HTTP 端到端耗时，每类 100 次请求。",72,429,1125,42,
  {fontSize:"19pt",color:de.muted});
text(s,"Reconciled result","全量清洗、双分片存储和查询结果已对账",72,507,1130,52,
  {fontSize:"29pt",bold:true,color:de.dark});
text(s,"Deployment limit","本次测试在一台主机上完成。多主机容错与并发负载有待验证。",72,582,1140,44,
  {fontSize:"18pt",color:de.muted});
s.speakerNotes.text="建议用时 35 秒\n每类接口预热十次后发一百次请求。用户轨迹只访问一个分片，P95 是 56.2 毫秒。区域查询访问两片，P95 为 525.8 毫秒。两种负载的筛选条件和结果规模也不同，不能将延时差异完全归因于分片数。两类请求都没有错误。整个案例完成了清洗输出、实际分片记录与查询结果的对账。本次结果对应单机双分片部署，多主机故障和并发负载需要进一步测试。";

await fs.mkdir(destination,{recursive:true});
for(let i=0;i<deck.slides.items.length;i++){
  const png=await deck.export({slide:deck.slides.items[i],format:"png",scale:1});
  await fs.writeFile(path.join(build,"slide-"+(i+1)+".png"),new Uint8Array(await png.arrayBuffer()));
}
const draft=path.join(build,"presentation-draft.pptx");
await (await PresentationFile.exportPptx(deck)).save(draft);
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,"container_tools","artifact_tool_utils.mjs")).href);
const result=await finalizePresentation({
  workspaceDir:root,candidatePath:draft,
  finalPath:path.join(destination,"presentation-final.pptx"),
  pythonExecutable:python,
  integrityValidatorPath:path.join(skill,"container_tools","inspect_presentation_package_integrity.py"),
  layoutValidatorPath:path.join(skill,"container_tools","inspect_presentation_layout_geometry.py"),
  layoutArgs:["--expected-slide-size-emu","12192000,6858000","--validate-heading-fit",
    "--require-native-table-slide","4","--require-native-table-slide","5","--require-native-table-slide","7","--require-native-table-slide","9"],
  explicitTotalSlideCount:9,requiredNativeTableOwnerSlides:[4,5,7,9],
  fontPolicy:{basis:"design",families:[font]},
  verifyArtifactToolImport:true,receiptPath:path.join(build,"presentation.final.validation.json"),
});
console.log(result);
