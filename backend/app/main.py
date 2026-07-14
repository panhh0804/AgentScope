"""
main.py —— AgentScope FastAPI 后端服务入口模块

该模块负责启动和初始化整个后端 RESTful API 服务，包括：
  1. 通过 dotenv 加载本地或集群层级的环境变量
  2. 实例化 FastAPI 核心应用
  3. 配置跨域 CORS 中间件（允许前端浏览器无障碍跨域访问）
  4. 挂载 v1 路由分发器 api_router 到 "/api/v1" 前缀下
  5. 暴露 "/health" 服务存活探测端点，供 Nginx 或集群探针进行心跳巡检
"""

# 在加载其他模块前，必须先加载环境变量以确保全局参数正确就绪
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router


# 初始化 FastAPI 服务实例
app = FastAPI(
    title="AgentScope API",
    version="0.1.0",
    description="Realtime and offline analytics API for AgentScope.",
)

# 注册 CORS 跨域安全中间件以允许前端 Web 控制台联调
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 允许所有域名接入（开发阶段）
    allow_credentials=True,         # 允许携带 Cookie 等凭证
    allow_methods=["*"],            # 允许所有请求类型 (GET, POST, OPTIONS 等)
    allow_headers=["*"],            # 允许所有自定义头部字段
)

# 挂载业务路由体系，区分版本号以提供向后兼容能力
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health() -> dict:
    """
    健康检查探测端点。

    Returns:
        dict: 固定返回状态健康对象 {"status": "ok"}
    """
    return {"status": "ok"}
