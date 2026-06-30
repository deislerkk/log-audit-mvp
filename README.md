# 日志审计智能体（MVP 原型）

说明
本原型包含：
- OpenSearch: 日志与审计记录存储
- Fluent Bit: 采集 /var/log/myapp.log 并发送到 OpenSearch
- log-generator: 持续生成示例日志到 /var/log/myapp.log
- audit-agent: Python 实现的审计智能体（基于 rules.yml 的检测 + 生成 audit 索引的链式哈希记录）

项目结构（请将所有文件按以下结构保存）：
.
├── docker-compose.yml
├── fluent-bit
│   └── fluent-bit.conf
├── logs
│   └── .gitkeep
├── log-generator
│   ├── Dockerfile
│   └── generator.py
└── audit-agent
    ├── Dockerfile
    ├── requirements.txt
    ├── audit_agent.py
    └── rules.yml

运行
1. 在项目根目录执行：
   docker compose up --build

2. 等待 OpenSearch 启动（可以通过 `docker compose logs opensearch` 查看），然后检查 audit-agent 日志：
   docker compose logs -f audit-agent

3. Fluent Bit 会将日志写入 OpenSearch 索引 `logs`，audit-agent 每 15 秒扫描一次 logs 索引并根据 rules.yml 检测异常。触发告警时，会把审计记录写入 `audit` 索引（包含 prev_hash 与 hash，形成链式哈希）。

查看数据
- 查看日志（通过浏览器或 curl）:
  curl -u admin:admin "http://localhost:9200/logs/_search?size=10" -H 'Content-Type: application/json' -d '{"query":{"match_all":{}},"sort":[{"@timestamp":{"order":"desc"}}]}'
- 查看审计记录:
  curl -u admin:admin "http://localhost:9200/audit/_search?size=10" -H 'Content-Type: application/json' -d '{"query":{"match_all":{}},"sort":[{"@timestamp":{"order":"desc"}}]}'

注意与改进建议
- 这是一个最小可运行原型，生产需要补充：
  - OpenSearch 的安全配置（TLS / 用户 / RBAC）
  - 并发场景下的审计 prev_hash 冲突处理（乐观锁 / 事务）
  - 更强的规则引擎（规则版本、抑制、降噪）、状态存储（避免重复告警）
  - 扩展到 Kafka / 分布式流处理用于高吞吐场景
  - 审计证据导出/API、WORM 存储或 S3 + Object Lock
  - 日志脱敏/PII 处理、告警推送（Slack/PagerDuty）

我已经把原型所有关键文件给出。如果你愿意：
- 我可以把这些文件整理成一个 Git 仓库并为你创建（需要你提供目标 repo 名称与授权），或者
- 我现在就把这个代码进一步增强：增加告警去重、增加审计导出 API、或把 audit-agent 改成异步并支持并发写入锁。

接下来你想要我做哪件事？
- A) 把这些文件推到 GitHub（请提供 owner/repo 或允许我在你的账号下创建）
- B) 增强 audit-agent（例如：加入告警抑制 / 去重 / web hook）
- C) 把原型转换为 Helm Chart 用于 K8s 部署
- D) 现在就把示例的更复杂规则（多事件关联）加入 rules.yml

如果没有进一步指示，我接下来可以把这些文件打包为一个 Git 仓库草稿供你下载/部署.
