# API 设计

统一前缀：

```text
/api/v1
```

统一响应：

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "request_id": "req_20260623_0001"
}
```

## 实时接口

| 方法 | 路径 | 数据来源 |
|---|---|---|
| GET | `/realtime/overview` | Redis |
| GET | `/realtime/trend?minutes=60` | Redis |
| GET | `/realtime/agents` | Redis |
| GET | `/realtime/alerts` | Redis |

## 历史分析接口

| 方法 | 路径 | 数据来源 |
|---|---|---|
| GET | `/metrics/daily?start_date=2026-06-01&end_date=2026-06-30` | MySQL Analytics |
| GET | `/metrics/hourly?date=2026-06-23` | MySQL Analytics |
| GET | `/rankings/agents?date=2026-06-23` | MySQL Analytics |
| GET | `/errors/distribution?date=2026-06-23` | MySQL Analytics |
| GET | `/graph/agent-relations?date=2026-06-23` | MySQL Analytics |
| GET | `/alerts/history?date=2026-06-23` | MySQL Analytics |

## 报告接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/reports/generate` | 基于结构化指标生成 Markdown 报告 |
| GET | `/reports` | 报告列表 |
| GET | `/reports/{report_id}` | 报告详情 |

