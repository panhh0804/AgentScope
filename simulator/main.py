"""
main.py —— AgentScope 模拟器的主程序入口

通过 argparse 命令行接口，接受多样的配置参数，支持：
  1. 实时模式 (--mode realtime)：流式向 Kafka 集群推送无限产生的实时事件。
  2. 离线模式 (--mode offline)：向 MySQL source 数据库或指定的本地 JSONL 文件写出批量生成的历史会话数据。
"""

from __future__ import annotations

import argparse
from datetime import date

from config_loader import load_config
from offline_generator import generate_events, write_jsonl, write_mysql
from realtime_producer import fatal, stream_events
from workflow_generator import SCENARIOS


def parse_date(value: str) -> date:
    """
    辅助命令行解析：将 'yyyy-MM-dd' 字符串解析为 date 对象。

    Args:
        value (str): 日期字符串

    Returns:
        date: 对应的日期对象
    """
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    """
    定义并构建命令行参数解析器。

    Returns:
        argparse.ArgumentParser: 参数解析器
    """
    parser = argparse.ArgumentParser(description="AgentScope event simulator")
    # 核心模式参数：实时 (realtime) 或离线 (offline)
    parser.add_argument("--mode", choices=["realtime", "offline"], required=True)
    # 可选外部配置文件路径
    parser.add_argument("--config", help="YAML config path, for example config/default.yaml")
    # 随机种子，确保生成的数据是一致、可复现的
    parser.add_argument("--seed", type=int, help="Seed for deterministic demo data")
    # 指定仿真场景
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="mixed")
    # 离线模式下的事件总数上限
    parser.add_argument("--count", type=int, default=1000, help="Offline workflow/trace count")
    # 离线模式的起止日期限制
    parser.add_argument("--start-date", type=parse_date, default=date.today())
    parser.add_argument("--end-date", type=parse_date, default=date.today())
    # 离线输出目标文件，如果不配置，则默认将数据入库到 MySQL
    parser.add_argument("--output", help="Offline JSONL output path. If omitted, write to MySQL.")

    # 实时模式参数
    parser.add_argument("--kafka-bootstrap")
    parser.add_argument("--kafka-topic")
    parser.add_argument("--rate", type=int, help="Realtime events per second")
    parser.add_argument("--stdout", action="store_true", help="Print realtime events as JSONL instead of sending Kafka")

    # 数据库连接参数覆盖
    parser.add_argument("--mysql-host")
    parser.add_argument("--mysql-port", type=int)
    parser.add_argument("--mysql-user")
    parser.add_argument("--mysql-password")
    parser.add_argument("--mysql-db")
    return parser


def main() -> None:
    """
    模拟器执行主入口函数。解析命令行，读取/合并配置，最终启动特定的流式推送或离线数据生成任务。
    """
    args = build_parser().parse_args()
    config = load_config(args.config)
    kafka_config = config.get("kafka", {})
    mysql_config = config.get("mysql", {})
    simulator_config = config.get("simulator", {})

    # 加载/覆盖实时传输 Kafka 的配置项
    kafka_bootstrap = args.kafka_bootstrap or kafka_config.get("bootstrap_servers", "middleware:9092")
    kafka_topic = args.kafka_topic or kafka_config.get("topic", "agent-events")
    rate = args.rate if args.rate is not None else int(simulator_config.get("default_rate", 10))

    # 加载/覆盖写入 MySQL 的配置项
    mysql_host = args.mysql_host or mysql_config.get("host", "middleware")
    mysql_port = args.mysql_port if args.mysql_port is not None else int(mysql_config.get("port", 3306))
    mysql_user = args.mysql_user or mysql_config.get("user", "agentscope")
    mysql_password = args.mysql_password or mysql_config.get("password", "agentscope_pass")
    mysql_db = args.mysql_db or mysql_config.get("database", "agentscope_source")

    # 1. 实时模式流处理仿真
    if args.mode == "realtime":
        try:
            stream_events(
                kafka_bootstrap,
                kafka_topic,
                rate,
                config=config,
                seed=args.seed,
                scenario=args.scenario,
                stdout=args.stdout,
            )
        except RuntimeError as exc:
            fatal(str(exc))
        return

    # 2. 离线模式批量模拟数据生成
    events = generate_events(
        args.count,
        args.start_date,
        args.end_date,
        config=config,
        seed=args.seed,
        scenario=args.scenario,
    )
    # 如果指定了 --output 选项，写出到本地 JSONL 文件
    if args.output:
        count = write_jsonl(events, args.output)
        print(f"wrote {count} events to {args.output}")
    # 否则直接执行批量 SQL 并行插入到 ODS 数据源表中
    else:
        count = write_mysql(
            events,
            host=mysql_host,
            port=mysql_port,
            user=mysql_user,
            password=mysql_password,
            database=mysql_db,
        )
        print(f"inserted {count} events into {mysql_db}.agent_events_source")


if __name__ == "__main__":
    main()
