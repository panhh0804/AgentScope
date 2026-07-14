"""
offline_generator.py —— AgentScope 模拟器的离线数据生成器

本模块支持“离线批量生成模式” (offline mode)。
能够一次性在指定的时间区间 (start_date ~ end_date) 内模拟出大量的链路调用事件。
生成完毕后，可以选择：
  1. 写入本地的 JSONL 文件 (write_jsonl) 格式，用作后续数据分析或流回放。
  2. 利用 PyMySQL 连接池直接注入 MySQL 原始源表 (write_mysql) 进行数仓分析调试。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Dict, Iterable, Iterator, Optional

from config_loader import DEFAULT_CONFIG
from event_model import AgentEvent
from workflow_generator import WorkflowGenerator


def generate_workflow_events(
    start_date: date,
    end_date: date,
    *,
    config: Optional[Dict] = None,
    seed: Optional[int] = None,
    scenario: str = "mixed",
) -> list[AgentEvent]:
    """
    生成一个完整会话工作流 (workflow) 中产生的所有 Agent 事件集合。

    Args:
        start_date (date): 仿真起始业务日期
        end_date (date): 仿真结束业务日期
        config (Optional[Dict]): 全局模拟配置
        seed (Optional[int]): 确定性随机种子
        scenario (str): 模拟的场景，默认为 "mixed"

    Returns:
        list[AgentEvent]: 包含整个会话链路所产生的完整事件列表
    """
    generator = WorkflowGenerator(config or DEFAULT_CONFIG, seed=seed, scenario=scenario)
    start_time = generator._offline_start_time(start_date, end_date)
    return generator.generate_workflow(start_time)


def generate_events(
    count: int,
    start_date: date,
    end_date: date,
    *,
    config: Optional[Dict] = None,
    seed: Optional[int] = None,
    scenario: str = "mixed",
) -> Iterator[AgentEvent]:
    """
    基于生成器按需流式迭代产生指定条数 (count) 的 Agent 事件。
    在时间窗口 (start_date ~ end_date) 之间以均匀分布的规律进行采样。

    Args:
        count (int): 需要生成的总事件行数
        start_date (date): 开始时间
        end_date (date): 结束时间
        config (Optional[Dict]): 模拟器参数
        seed (Optional[int]): 随机种子
        scenario (str): 模拟场景

    Returns:
        Iterator[AgentEvent]: AgentEvent 的流式迭代生成器
    """
    generator = WorkflowGenerator(config or DEFAULT_CONFIG, seed=seed, scenario=scenario)
    yield from generator.generate_events(count, start_date, end_date)


def write_jsonl(events: Iterable[AgentEvent], output: str) -> int:
    """
    将生成的事件列表按行转换为 JSON 字符串，保存到本地的 JSONL 文件中。

    Args:
        events (Iterable[AgentEvent]): 要写出的事件序列
        output (str): 输出文件的路径

    Returns:
        int: 实际成功写入的事件行数
    """
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as fp:
        for event in events:
            # 保证 key 排序以形成统一的序列化哈希
            fp.write(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def write_mysql(events: Iterable[AgentEvent], host: str, port: int, user: str, password: str, database: str) -> int:
    """
    利用 PyMySQL 建立连接，以批量预编译 (executemany) 的高效 SQL 方式
    将数据直接注入到 mysql source ODS 表中，支持主键冲突时更新覆盖。

    Args:
        events (Iterable[AgentEvent]): 要写出的事件序列
        host (str): MySQL 数据库地址
        port (int): MySQL 端口
        user (str): 账号
        password (str): 密码
        database (str): 数据库名称 (e.g. agentscope_source)

    Returns:
        int: 成功写入库的记录数量

    Raises:
        RuntimeError: 当没有安装 PyMySQL 依赖时抛出
    """
    try:
        import pymysql
    except ImportError as exc:
        raise RuntimeError("PyMySQL is required for MySQL output. Install simulator/requirements.txt") from exc

    # ODS 源库写入 SQL，注意在主键冲突时，会针对 status 和 latency_ms 执行原地更新，从而保证幂等性
    sql = """
    INSERT INTO agent_events_source (
      event_id, trace_id, run_id, parent_run_id, agent_id, parent_agent_id,
      agent_role, event_type, status, event_time, latency_ms,
      prompt_tokens, completion_tokens, total_tokens, cost_usd, model_name,
      tool_name, error_type, retry_count, metadata_json
    ) VALUES (
      %(event_id)s, %(trace_id)s, %(run_id)s, %(parent_run_id)s, %(agent_id)s, %(parent_agent_id)s,
      %(agent_role)s, %(event_type)s, %(status)s, %(timestamp)s, %(latency_ms)s,
      %(prompt_tokens)s, %(completion_tokens)s, %(total_tokens)s, %(cost_usd)s, %(model_name)s,
      %(tool_name)s, %(error_type)s, %(retry_count)s, %(metadata_json)s
    )
    ON DUPLICATE KEY UPDATE status = VALUES(status), latency_ms = VALUES(latency_ms)
    """

    rows = []
    for event in events:
        item = event.to_dict()
        # 将标准 ISO 时间中的 'T' 字符替换为空格，以符合 MySQL 的 DATETIME 数据类型格式要求
        item["timestamp"] = item["timestamp"].replace("T", " ").split("+")[0]
        # 对元数据字典进行序列化转为 JSON 字符串
        item["metadata_json"] = json.dumps(item["metadata_json"], ensure_ascii=False, sort_keys=True)
        rows.append(item)

    if not rows:
        return 0

    # 建立数据库会话，批量插入数据
    conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset="utf8mb4")
    try:
        with conn.cursor() as cursor:
            cursor.executemany(sql, rows)
        conn.commit()
        return len(rows)
    finally:
        conn.close()
