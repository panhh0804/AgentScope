from __future__ import annotations

import argparse
from datetime import date

from offline_generator import generate_events, write_jsonl, write_mysql
from realtime_producer import stream_events


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AgentScope event simulator")
    parser.add_argument("--mode", choices=["realtime", "offline"], required=True)
    parser.add_argument("--count", type=int, default=1000, help="Offline event count")
    parser.add_argument("--start-date", type=parse_date, default=date.today())
    parser.add_argument("--end-date", type=parse_date, default=date.today())
    parser.add_argument("--output", help="Offline JSONL output path. If omitted, write to MySQL.")

    parser.add_argument("--kafka-bootstrap", default="middleware:9092")
    parser.add_argument("--kafka-topic", default="agent-events")
    parser.add_argument("--rate", type=int, default=10, help="Realtime events per second")

    parser.add_argument("--mysql-host", default="middleware")
    parser.add_argument("--mysql-port", type=int, default=3306)
    parser.add_argument("--mysql-user", default="agentscope")
    parser.add_argument("--mysql-password", default="agentscope_pass")
    parser.add_argument("--mysql-db", default="agentscope_source")
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.mode == "realtime":
        stream_events(args.kafka_bootstrap, args.kafka_topic, args.rate)
        return

    events = generate_events(args.count, args.start_date, args.end_date)
    if args.output:
        count = write_jsonl(events, args.output)
        print(f"wrote {count} events to {args.output}")
    else:
        count = write_mysql(
            events,
            host=args.mysql_host,
            port=args.mysql_port,
            user=args.mysql_user,
            password=args.mysql_password,
            database=args.mysql_db,
        )
        print(f"inserted {count} events into {args.mysql_db}.agent_events_source")


if __name__ == "__main__":
    main()

