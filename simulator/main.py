from __future__ import annotations

import argparse
from datetime import date

from config_loader import load_config
from offline_generator import generate_events, write_jsonl, write_mysql
from realtime_producer import fatal, stream_events
from workflow_generator import SCENARIOS


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AgentScope event simulator")
    parser.add_argument("--mode", choices=["realtime", "offline"], required=True)
    parser.add_argument("--config", help="YAML config path, for example config/default.yaml")
    parser.add_argument("--seed", type=int, help="Seed for deterministic demo data")
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="mixed")
    parser.add_argument("--count", type=int, default=1000, help="Offline workflow/trace count")
    parser.add_argument("--start-date", type=parse_date, default=date.today())
    parser.add_argument("--end-date", type=parse_date, default=date.today())
    parser.add_argument("--output", help="Offline JSONL output path. If omitted, write to MySQL.")

    parser.add_argument("--kafka-bootstrap")
    parser.add_argument("--kafka-topic")
    parser.add_argument("--rate", type=int, help="Realtime events per second")
    parser.add_argument("--stdout", action="store_true", help="Print realtime events as JSONL instead of sending Kafka")

    parser.add_argument("--mysql-host")
    parser.add_argument("--mysql-port", type=int)
    parser.add_argument("--mysql-user")
    parser.add_argument("--mysql-password")
    parser.add_argument("--mysql-db")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config(args.config)
    kafka_config = config.get("kafka", {})
    mysql_config = config.get("mysql", {})
    simulator_config = config.get("simulator", {})

    kafka_bootstrap = args.kafka_bootstrap or kafka_config.get("bootstrap_servers", "middleware:9092")
    kafka_topic = args.kafka_topic or kafka_config.get("topic", "agent-events")
    rate = args.rate if args.rate is not None else int(simulator_config.get("default_rate", 10))

    mysql_host = args.mysql_host or mysql_config.get("host", "middleware")
    mysql_port = args.mysql_port if args.mysql_port is not None else int(mysql_config.get("port", 3306))
    mysql_user = args.mysql_user or mysql_config.get("user", "agentscope")
    mysql_password = args.mysql_password or mysql_config.get("password", "agentscope_pass")
    mysql_db = args.mysql_db or mysql_config.get("database", "agentscope_source")

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

    events = generate_events(
        args.count,
        args.start_date,
        args.end_date,
        config=config,
        seed=args.seed,
        scenario=args.scenario,
    )
    if args.output:
        count = write_jsonl(events, args.output)
        print(f"wrote {count} events to {args.output}")
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

