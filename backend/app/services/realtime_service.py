"""
realtime_service.py —— AgentScope 实时流与集群组件监控服务

本模块作为实时大屏后端服务，负责处理：
  1. 集群中间件与服务节点的存活及效能探测 (get_middleware_stats)：
     - MySQL: 检查 TCP 连接时延，运行 SHOW GLOBAL STATUS 提取连接数与 QPS 指标。
     - Redis: 检查 PING 连通性，运行 INFO 指标抓取缓存使用量与 OPS 频率。
     - Kafka: 检查 Broker TCP 端口，通过 Redis 实时吞吐折算并发速率。
     - YARN: 运行 REST Web API 获取正在运行的任务 (appsRunning)、资源占比分配。
     - HDFS: 通过 WebHDFS 的 JMX JSON 节点查询活跃与失效 DataNode (NumLiveDataNodes)。
     - Spark: 通过 YARN 任务列表过滤捕获处于 RUNNING 的 Spark 工程项目。
  2. 读取 Redis 的实时数据 (overview, trend, agents, alerts)：
     - 这部分键值通常是由 Spark Streaming 作业实时写入 Redis，
     - 当 Redis 不可用时，通过 DATA_MODE 决定是否自动回退至 mock_data 以保证监控大屏正常运作。
"""

from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.services import mock_data


class RealtimeService:
    """
    实时计算指标与组件运维探测服务层。
    """
    def __init__(self) -> None:
        """
        初始化服务，预置中间件探测的缓存窗口以降低频繁网络 I/O 损耗。
        """
        self._redis = None
        self._middleware_cache: Optional[List[Dict[str, Any]]] = None
        self._middleware_cache_at = 0.0

    def _client(self):
        """
        延迟连接并返回 Redis 客户端单例。如果连接不通，则返回 False 以便业务知晓降级。
        """
        if self._redis is not None:
            return self._redis
        try:
            import redis

            self._redis = redis.Redis(
                host=os.getenv("REDIS_HOST", "middleware"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0")),
                decode_responses=True,
                socket_connect_timeout=0.2, # 限制短超时，防阻塞后端主线程
                socket_timeout=0.2,
            )
            self._redis.ping()
        except Exception:
            self._redis = False
        return self._redis

    def _get_json(self, key: str) -> Optional[Any]:
        """
        读取 Redis 的指定键值并反序列化为 JSON 字典/列表。
        """
        client = self._client()
        if not client:
            return None
        value = client.get(key)
        if not value:
            return None
        return json.loads(value)

    def _data_mode(self) -> str:
        """
        数据模式：strict 严格模式或带有 Mock 降级的普通模式。
        """
        return os.getenv("DATA_MODE", "demo").lower()

    def _with_success_rate(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        if overview.get("success_rate") is not None:
            return overview
        try:
            success_count = int(overview.get("success_count") or 0)
            failed_count = int(overview.get("failed_count") or 0)
        except (TypeError, ValueError):
            overview["success_rate"] = None
            return overview

        total_finished = success_count + failed_count
        overview["success_rate"] = success_count / total_finished if total_finished > 0 else None
        return overview

    def _middleware_host(self) -> str:
        return os.getenv("MIDDLEWARE_HOST", "middleware")

    def _hadoop_host(self) -> str:
        return os.getenv("HADOOP_HOST", os.getenv("YARN_HOST", "master"))

    def _tcp_probe(self, host: str, port: int, timeout: float = 0.35) -> Dict[str, Any]:
        """
        轻量级 TCP 握手探测，测试端口存活性以及连接网络延迟（RTT 往返时延）。

        Args:
            host (str): 目标主机 IP/域名
            port (int): 目标 TCP 端口
            timeout (float): 超时限制（秒）

        Returns:
            Dict[str, Any]: {"ok": Bool, "latency_ms": 延迟毫秒数, "reason": 错误详情}
        """
        start = time.perf_counter()
        try:
            with socket.create_connection((host, port), timeout=timeout):
                latency_ms = round((time.perf_counter() - start) * 1000, 1)
                return {"ok": True, "latency_ms": latency_ms, "reason": None}
        except OSError as exc:
            return {"ok": False, "latency_ms": None, "reason": str(exc)}

    def _http_json(self, url: str, timeout: float = 0.5) -> Optional[Dict[str, Any]]:
        """
        标准轻量级 HTTP GET 请求，获取 REST API 响应并反序列化为 JSON 字典。
        """
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                if response.status >= 400:
                    return None
                return json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError):
            return None

    def _service_row(
        self,
        name: str,
        host: str,
        port: int,
        ok: bool,
        metric: str,
        hint: str,
        status_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        快速构造用于可视化表格输出的组件状态行。
        """
        return {
            "name": name,
            "status": "normal" if ok else "warning",
            "statusLabel": status_label or ("RUNNING" if ok else "DOWN"),
            "metric": metric,
            "host": host,
            "port": port,
            "hint": hint,
        }

    def _mysql_stats(self) -> Dict[str, Any]:
        """
        探测并抓取 MySQL 数据库的存活和并发连接、QPS 性能数据。
        """
        host = os.getenv("MYSQL_HOST", self._middleware_host())
        port = int(os.getenv("MYSQL_PORT", "3306"))
        probe = self._tcp_probe(host, port)
        if not probe["ok"]:
            return self._service_row("MySQL 关系数据库", host, port, False, "DOWN", probe["reason"] or "connect timeout")

        connections = None
        uptime = None
        questions = None
        try:
            import pymysql

            conn = pymysql.connect(
                host=host,
                port=port,
                user=os.getenv("MYSQL_USER", "agentscope"),
                password=os.getenv("MYSQL_PASSWORD", "agentscope_pass"),
                database=os.getenv("MYSQL_ANALYTICS_DB", "agentscope_analytics"),
                connect_timeout=0.5,
                read_timeout=0.5,
                write_timeout=0.5,
            )
            with conn.cursor() as cur:
                cur.execute("SHOW GLOBAL STATUS WHERE Variable_name IN ('Threads_connected', 'Uptime', 'Questions')")
                rows = dict(cur.fetchall())
            conn.close()
            connections = int(rows.get("Threads_connected") or 0)
            uptime = int(rows.get("Uptime") or 0)
            questions = int(rows.get("Questions") or 0)
        except Exception as exc:
            return self._service_row(
                "MySQL 关系数据库",
                host,
                port,
                False,
                "AUTH/QUERY FAIL",
                f"port open, query failed: {exc}",
                "CHECK",
            )

        qps = round(questions / uptime, 1) if uptime else 0
        return self._service_row(
            "MySQL 关系数据库",
            host,
            port,
            True,
            f"{connections} conns / {qps} QPS",
            f"latency {probe['latency_ms']} ms",
        )

    def _redis_stats(self) -> Dict[str, Any]:
        """
        探测并抓取 Redis 缓存节点的存活、内存负载及吞吐统计。
        """
        host = os.getenv("REDIS_HOST", self._middleware_host())
        port = int(os.getenv("REDIS_PORT", "6379"))
        probe = self._tcp_probe(host, port)
        if not probe["ok"]:
            return self._service_row("Redis 缓存/实时指标", host, port, False, "DOWN", probe["reason"] or "connect timeout")

        try:
            client = self._client()
            if not client or isinstance(client, bool):
                raise RuntimeError("redis client unavailable")
            info = client.info()
            memory = info.get("used_memory_human", "-")
            ops = info.get("instantaneous_ops_per_sec", 0)
            clients = info.get("connected_clients", 0)
        except Exception as exc:
            return self._service_row(
                "Redis 缓存/实时指标",
                host,
                port,
                False,
                "PING FAIL",
                f"port open, info failed: {exc}",
                "CHECK",
            )

        return self._service_row(
            "Redis 缓存/实时指标",
            host,
            port,
            True,
            f"{memory} / {ops} ops/s",
            f"{clients} clients, {probe['latency_ms']} ms",
        )

    def _kafka_stats(self) -> Dict[str, Any]:
        """
        检测 Kafka 消息队列代理端口可达性以及消息消费观测流速。
        """
        bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", f"{self._middleware_host()}:9092").split(",")[0].strip()
        host, _, port_text = bootstrap.partition(":")
        port = int(port_text or "9092")
        probe = self._tcp_probe(host, port)
        if not probe["ok"]:
            return self._service_row("Kafka 消息队列", host, port, False, "DOWN", probe["reason"] or "connect timeout")

        overview = self._get_json("agentscope:realtime:overview") or {}
        events_per_minute = overview.get("events_per_minute", 0) if isinstance(overview, dict) else 0
        try:
            msg_rate = round(float(events_per_minute) / 60, 2)
        except (TypeError, ValueError):
            msg_rate = 0
        metric = f"{msg_rate} msg/s observed" if msg_rate else "port open"
        return self._service_row(
            "Kafka 消息队列",
            host,
            port,
            True,
            metric,
            f"broker tcp {probe['latency_ms']} ms",
        )

    def _yarn_stats(self) -> Dict[str, Any]:
        """
        探测 YARN 集群可用性、活跃 application 状态及分配内存负载。
        """
        host = os.getenv("YARN_HOST", self._hadoop_host())
        port = int(os.getenv("YARN_PORT", "8088"))
        probe = self._tcp_probe(host, port)
        if not probe["ok"]:
            return self._service_row("YARN 资源调度", host, port, False, "DOWN", probe["reason"] or "connect timeout")

        # 从 YARN ResourceManager REST API 抓取度量结构
        metrics = self._http_json(f"http://{host}:{port}/ws/v1/cluster/metrics")
        if not metrics:
            return self._service_row(
                "YARN 资源调度",
                host,
                port,
                True,
                "web open",
                f"REST unavailable, tcp {probe['latency_ms']} ms",
                "CHECK",
            )
        cluster = metrics.get("clusterMetrics", {})
        running_apps = cluster.get("appsRunning", 0)
        allocated = cluster.get("allocatedMB", 0)
        available = cluster.get("availableMB", 0)
        return self._service_row(
            "YARN 资源调度",
            host,
            port,
            True,
            f"{running_apps} apps / {allocated}MB used",
            f"{available}MB available",
        )

    def _hdfs_stats(self) -> Dict[str, Any]:
        """
        调用 NameNode 的 JMX REST 接口，分析底层存储系统的存活 DataNode 分布。
        """
        host = os.getenv("HDFS_NAMENODE_HOST", self._hadoop_host())
        port = int(os.getenv("HDFS_NAMENODE_WEB_PORT", "50070"))
        probe = self._tcp_probe(host, port)
        if not probe["ok"]:
            return self._service_row("HDFS NameNode", host, port, False, "DOWN", probe["reason"] or "connect timeout")

        # 使用 WebHDFS 的 JMX 查询节点系统状态
        jmx = self._http_json(
            f"http://{host}:{port}/jmx?qry=Hadoop:service=NameNode,name=FSNamesystemState"
        )
        if jmx and jmx.get("beans"):
            bean = jmx["beans"][0]
            live_nodes = bean.get("NumLiveDataNodes", 0)
            dead_nodes = bean.get("NumDeadDataNodes", 0)
            files = bean.get("FilesTotal", 0)
            # 如果存在宕机 DataNode，或者活节点数量为 0，则判定为非健康警告状态 (degraded)
            ok = int(dead_nodes or 0) == 0 and int(live_nodes or 0) > 0
            return self._service_row(
                "HDFS NameNode",
                host,
                port,
                ok,
                f"{live_nodes} live / {dead_nodes} dead",
                f"{files} files",
                "RUNNING" if ok else "DEGRADED",
            )

        return self._service_row(
            "HDFS NameNode",
            host,
            port,
            True,
            "web open",
            f"JMX unavailable, tcp {probe['latency_ms']} ms",
            "CHECK",
        )

    def _spark_stats(self) -> Dict[str, Any]:
        """
        监控 Spark 框架在集群中的计算实例状况。
        """
        spark_master = os.getenv("SPARK_MASTER", os.getenv("SPARK_MASTER_URL", "yarn"))
        yarn_host = os.getenv("YARN_HOST", self._hadoop_host())
        yarn_port = int(os.getenv("YARN_PORT", "8088"))

        if spark_master == "yarn":
            # 如果是 YARN 托管模式，从 YARN App 列表中过滤筛选计算中的 Spark 程序
            apps = self._http_json(f"http://{yarn_host}:{yarn_port}/ws/v1/cluster/apps?states=RUNNING")
            if apps is not None:
                running = apps.get("apps", {}).get("app") or []
                spark_apps = [app for app in running if "spark" in str(app.get("applicationType", "")).lower()]
                return self._service_row(
                    "Spark on YARN",
                    yarn_host,
                    yarn_port,
                    True,
                    f"{len(spark_apps)} running apps",
                    "checked by YARN REST",
                )
            return self._service_row("Spark on YARN", yarn_host, yarn_port, False, "DOWN", "YARN REST unavailable")

        # Standalone 单机托管模式下探测 Spark Master 物理端口
        host = os.getenv("SPARK_MASTER_HOST", self._hadoop_host())
        port = int(os.getenv("SPARK_MASTER_WEB_PORT", "8080"))
        probe = self._tcp_probe(host, port)
        if probe["ok"]:
            return self._service_row(
                "Spark Standalone",
                host,
                port,
                True,
                "master web open",
                f"tcp {probe['latency_ms']} ms",
            )

        return self._service_row("Spark Standalone", host, port, False, "DOWN", probe["reason"] or "connect timeout")

    def get_middleware_stats(self) -> List[Dict[str, Any]]:
        """
        汇总并获取整个中间件技术栈的运行健康矩阵。具备 5 秒以内的轻量级缓存，避免并发 HTTP 请求冲击被测服务端口。
        """
        now = time.monotonic()
        if self._middleware_cache and now - self._middleware_cache_at < 5:
            return self._middleware_cache

        checks = [
            self._mysql_stats,
            self._redis_stats,
            self._kafka_stats,
            self._yarn_stats,
            self._hdfs_stats,
            self._spark_stats,
        ]
        rows: List[Dict[str, Any]] = []
        for check in checks:
            try:
                rows.append(check())
            except Exception as exc:
                rows.append(
                    self._service_row(
                        check.__name__.replace("_", " ").strip(),
                        "-",
                        0,
                        False,
                        "CHECK FAIL",
                        str(exc),
                        "ERROR",
                    )
                )
        self._middleware_cache = rows
        self._middleware_cache_at = now
        return rows

    def overview(self) -> Dict:
        """
        获取实时大屏的指标卡片全局数据（含中间件健康度数据矩阵）。
        """
        redis_data = self._get_json("agentscope:realtime:overview")
        middleware_stats = self.get_middleware_stats()
        if redis_data and isinstance(redis_data, dict):
            redis_data = self._with_success_rate(redis_data)
            redis_data["middleware"] = middleware_stats
            return {"data": redis_data, "data_source": "redis", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": {"middleware": middleware_stats}, "data_source": "redis", "fallback": False, "reason": "Redis unavailable or empty"}
        overview = mock_data.realtime_overview()
        overview = self._with_success_rate(overview)
        overview["middleware"] = middleware_stats
        return {"data": overview, "data_source": "mock", "fallback": True, "reason": "Redis unavailable or empty"}

    def trend(self, minutes: int) -> Dict:
        """
        读取并计算实时指标的秒级变化走势趋势。若 Redis 可连接，还会自动将最新概览写入折线样本，形成历史滚动的 60 个刻度点。
        """
        client = self._client()
        if client:
            overview_raw = client.get("agentscope:realtime:overview")
            if overview_raw:
                try:
                    overview = json.loads(overview_raw)
                    from datetime import datetime
                    now_str = datetime.now().isoformat(timespec="seconds")
                    
                    trend_raw = client.get("agentscope:realtime:trend")
                    trend_list = json.loads(trend_raw) if trend_raw else []
                    
                    # 避免在同一秒内向 Redis 的滑动队列中重复推送重复的时点记录
                    if not trend_list or trend_list[-1].get("time") != now_str:
                        new_point = {
                            "time": now_str,
                            "events": overview.get("events_per_minute", 0),
                            "success": overview.get("success_count", 0),
                            "failed": overview.get("failed_count", 0),
                            "avg_latency_ms": overview.get("avg_latency_ms", 0),
                        }
                        trend_list.append(new_point)
                        # 最长只在缓存中保留 60 秒的历史滑动轨迹，防止内存无限膨胀
                        trend_list = trend_list[-60:]
                        client.set("agentscope:realtime:trend", json.dumps(trend_list), ex=600)
                except Exception:
                    pass
            data = self._get_json("agentscope:realtime:trend")
            if data:
                return {"data": data[-minutes:], "data_source": "redis", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "redis", "fallback": False, "reason": "Redis unavailable or empty"}
        return {"data": mock_data.realtime_trend(minutes), "data_source": "mock", "fallback": True, "reason": "Redis unavailable or empty"}

    def agents(self) -> Dict:
        """
        读取 Redis 缓存中的智能体实时执行状态与性能数据。
        """
        redis_data = self._get_json("agentscope:realtime:agents")
        if redis_data:
            return {"data": redis_data, "data_source": "redis", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "redis", "fallback": False, "reason": "Redis unavailable or empty"}
        return {"data": mock_data.realtime_agents(), "data_source": "mock", "fallback": True, "reason": "Redis unavailable or empty"}

    def alerts(self) -> Dict:
        """
        读取实时监控系统当前被推送触发的所有活动中（未关闭）的告警。
        """
        redis_data = self._get_json("agentscope:realtime:alerts")
        if redis_data:
            return {"data": redis_data, "data_source": "redis", "fallback": False, "reason": None}
        if self._data_mode() == "strict":
            return {"data": [], "data_source": "redis", "fallback": False, "reason": "Redis unavailable or empty"}
        return {"data": mock_data.recent_alerts(), "data_source": "mock", "fallback": True, "reason": "Redis unavailable or empty"}
