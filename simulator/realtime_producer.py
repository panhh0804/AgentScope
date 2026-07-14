"""
realtime_producer.py —— AgentScope 模拟器的实时数据生产者

该模块负责处理“实时模式” (realtime mode) 下的数据流推送。
它利用 WorkflowGenerator 持续生成无限的 Agent 运行事件流，
并通过 kafka-python 客户端，以指定的速率 (rate) 异步投递到 Kafka 的对应 Topic 中。
如果开启了 stdout 模式，则仅将生成的事件序列化并打印到标准输出，用作 Debug 或本地管道传输。
"""

from __future__ import annotations

import json
import sys
import time
from typing import Dict, Iterable, Optional

from config_loader import DEFAULT_CONFIG
from event_model import AgentEvent
from workflow_generator import WorkflowGenerator


def _producer(bootstrap_servers: str):
    """
    内部辅助函数：初始化并返回一个 KafkaProducer 实例。

    Args:
        bootstrap_servers (str): Kafka Broker 的网络接入地址，例如 'middleware:9092'

    Returns:
        KafkaProducer: 已经成功握手的 Kafka 生产者客户端实例

    Raises:
        RuntimeError: 当 kafka-python 依赖缺失或 Kafka 建立连接失败时抛出
    """
    try:
        from kafka import KafkaProducer
    except ImportError as exc:
        raise RuntimeError("kafka-python is required for realtime mode. Install simulator/requirements.txt") from exc
    try:
        return KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            # 将字典序列化为 UTF-8 编码的 JSON 字节流
            value_serializer=lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8"),
            linger_ms=50,       # 延迟发送策略（50ms），在吞吐量与时延之间寻找平衡
            retries=3,          # 自动重试 3 次，防止网络瞬态故障
        )
    except Exception as exc:
        raise RuntimeError(f"failed to connect to Kafka bootstrap servers: {bootstrap_servers}") from exc


def stream_events(
    bootstrap_servers: str,
    topic: str,
    rate: int,
    *,
    config: Optional[Dict] = None,
    seed: Optional[int] = None,
    scenario: str = "mixed",
    stdout: bool = False,
) -> None:
    """
    核心实时流启动方法。以指定频率生成并投递 AgentEvent 消息。

    Args:
        bootstrap_servers (str): Kafka 集群入口地址
        topic (str): 投递的目标 Kafka Topic 名称
        rate (int): 每秒发送的事件数量控制上限
        config (Optional[Dict]): 自定义模拟配置
        seed (Optional[int]): 随机种子（开启确定性模拟使用）
        scenario (str): 模拟的会话场景，取值如 "mixed"、"success" 等
        stdout (bool): 若为 True，则把事件以 stdout 形式流式输出，不建立 Kafka 链接
    """
    generator = WorkflowGenerator(config or DEFAULT_CONFIG, seed=seed, scenario=scenario)
    sleep_seconds = 1.0 / max(rate, 1) # 根据速率计算发送时间差
    events = generator.generate_realtime_events()

    # 1. 纯控制台输出模式 (Debug/命令行调试管道)
    if stdout:
        for event in events:
            print(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True), flush=True)
            time.sleep(sleep_seconds)
        return

    # 2. 真实 Kafka 发送模式
    producer = _producer(bootstrap_servers)
    try:
        for event in events:
            producer.send(topic, event.to_dict())
            time.sleep(sleep_seconds)
    finally:
        # 在退出循环或发生异常时，确保缓冲区残留的事件全部冲刷发送并安全关闭
        producer.flush()
        producer.close()


def print_events(events: Iterable[AgentEvent]) -> None:
    """
    打印传入的事件集合，主要用作调试输出。

    Args:
        events (Iterable[AgentEvent]): 需要打印的事件迭代器
    """
    for event in events:
        print(json.dumps(event.to_dict(), ensure_ascii=False, sort_keys=True))


def fatal(message: str) -> None:
    """
    辅助诊断：向标准错误输出错误信息并以状态码 1 退出进程。

    Args:
        message (str): 错误信息
    """
    print(message, file=sys.stderr)
    raise SystemExit(1)
