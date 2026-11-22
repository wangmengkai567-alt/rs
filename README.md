# Gowalla 签到数据服务

课程作业实现。系统读取课程下发的签到文件，清洗后通过 MongoDB 路由写入两个分片。FastAPI 提供用户轨迹、区域签到、统计概览和质量报告，首页提供地图与查询表格。

## 运行环境

使用 Docker Desktop（Linux 容器）或支持 Docker Compose 的 Docker Engine，以及 uv。项目锁定 Python 3.11，数据库镜像为 MongoDB 7.0。数据库路由和 API 分别监听本机的 27017、8000 端口。首次启动需要联网下载镜像和 Python 依赖，地图底图由 OpenStreetMap 提供。

在项目根目录执行以下命令。

~~~powershell
uv sync --locked
docker compose up -d
docker wait (docker compose ps -a -q sharding-init)
docker compose ps -a
~~~

初始化任务先启动三个单成员副本集，再通过 mongos 添加两个数据分片并配置 user_id 哈希分片。docker wait 输出 0 表示 sharding-init 成功。docker compose ps -a 应显示 mongos 为 healthy。

## 清洗、导入与启动

将下发的归档解压到对应目录后运行。

~~~powershell
uv run --locked python -m cleaner.pipeline --input "测试数据loc-gowalla_totalCheckins.txt/Gowalla_totalCheckins.txt" --output output
uv run --locked python -m db.import_checkins --input output/clean.tsv --report output/quality_report.json
uv run --locked uvicorn api.main:app --host 127.0.0.1 --port 8000
~~~

打开 [地图查询](http://127.0.0.1:8000/) 或 [API 文档](http://127.0.0.1:8000/docs)。清洗输出位于 output，包含 clean.tsv、reject.ndjson 和 quality_report.json。导入中断后，重新执行同一条导入命令。程序以 5,000 条为一批，最多并发写入四批，使用完整分片键和源文件行号匹配已写入记录。索引和计数核对通过后开放数据查询。

## 验收

在另一个 PowerShell 窗口运行以下命令，查看总记录数、两个分片的数据分布和两类查询的执行计划。

~~~powershell
docker compose cp db/verify_distribution.js mongos:/tmp/verify_distribution.js
docker compose exec -T mongos mongosh --quiet --file /tmp/verify_distribution.js
~~~

- 清洗输入为 6,442,892 条，通过 6,442,127 条，拒收 765 条。原因分别为越界 29 条、双零坐标 135 条、重复 601 条。
- 两片持有的记录数都应大于零，合计为 6,442,127。用户 0 的轨迹执行计划应只涉及一个分片，城市区域查询应访问两个分片。
- 用户 0 的完整轨迹有 225 条。用奥斯汀范围 -97.81,30.22,-97.74,30.30 和 UTC 半开区间 [2010-10-19T23:55:27Z, 2010-10-19T23:55:28Z) 查询，应包含源文件第 1 行。

### 本机全量实测

| 分片 | 持有签到 |
| --- | ---: |
| shard1 | 3,230,580 |
| shard2 | 3,211,547 |
| 合计 | 6,442,127 |

从同一清洗文件重跑导入后，匹配 1,190,000 条已写记录，新增 5,252,127 条。新版接口复测中，用户轨迹和区域查询各发起 100 次请求，失败分别为 0 次和 13 次。成功请求的 P95 分别为 472.9 ms 和 11618.9 ms。全量运行产物包括 [质量报告](output/quality_report.json)、[验收记录](output/acceptance.json) 和 [演示截图](output/preview.png)。

## 停止 Docker 服务

演示结束后，在项目根目录执行以下命令。

~~~powershell
docker compose stop
docker compose ps -a
~~~

数据库容器停止后会显示为 `Exited`。签到数据保存在 Docker 数据卷中，下次执行 `docker compose up -d` 即可继续使用。

地图使用本地分发的 Leaflet 1.9.4，许可见 [Leaflet LICENSE](web/static/leaflet/LICENSE)。
