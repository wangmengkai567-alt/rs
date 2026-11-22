# Gowalla 签到数据服务

系统清洗课程下发的 Gowalla 签到数据，经 MongoDB 路由写入两台电脑各自的数据分片。FastAPI 提供用户轨迹、区域签到、统计概览和清洗报告。首页用 Leaflet 展示地图和查询结果。

## 两台电脑部署与验收

A 机运行 `shard1`、配置服务器、`mongos` 和 FastAPI，B 机运行 `shard2`。两台电脑各自启动本地 Docker 引擎，使用同一局域网中的两个不同 IPv4 地址。A 机还需 uv，项目锁定 Python 3.11。两台电脑首次启动时会下载 MongoDB 7.0 镜像。

按[双机部署与验收手册](docs/双机部署与验收.md)配置地址，先启动 B 机，再启动 A 机。全量导入完成后，由 B 机导出本地存储证据，A 机将该证据与直连计数、路由计数和查询执行计划对账。

## 在 A 机清洗、导入与启动

完成双机集群初始化后，在 A 机项目根目录运行。清洗输入使用解压后的课程附件。

~~~powershell
uv sync --locked
uv run --locked python -m cleaner.pipeline --input "测试数据loc-gowalla_totalCheckins.txt/Gowalla_totalCheckins.txt" --output output
uv run --locked python -m db.import_checkins --input output/clean.tsv --report output/quality_report.json
uv run --locked uvicorn api.main:app --host 127.0.0.1 --port 8000
~~~

打开 [地图查询](http://127.0.0.1:8000/) 或 [API 文档](http://127.0.0.1:8000/docs)。导入中断后，可重跑同一份清洗文件。程序使用完整分片键和源文件行号匹配已写记录，索引和计数核对通过后开放查询。

此前报告中的 3,230,580 与 3,211,547 条分片计数及查询耗时来自单机双容器实验。跨实体机结果以[双机部署与验收手册](docs/双机部署与验收.md)生成的记录为准。

## 停止 Docker 服务

演示结束后，先在 A 机的项目根目录执行。

~~~powershell
docker compose stop
docker compose ps -a
~~~

再在 B 机的项目根目录执行。

~~~powershell
docker compose -f compose.peer.yaml stop
docker compose -f compose.peer.yaml ps -a
~~~

数据库容器停止后会显示为 `Exited`，数据保存在两台电脑各自的 Docker 数据卷中。下次按启动顺序先启动 B 机，再启动 A 机。

地图使用本地分发的 Leaflet 1.9.4，许可见 [Leaflet LICENSE](web/static/leaflet/LICENSE)。
