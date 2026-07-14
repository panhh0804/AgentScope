"""
agents/__init__.py —— AgentScope 模拟器的智能体角色定义

本模块定义了在一个完整的多智能体会话工作流中参与协作的各种 Agent 角色身份。
标准的协作顺序为：
  Planner (规划者) -> Search (搜索者) -> Analysis (分析者) -> Writer (撰写者) -> Reviewer (评审者)
"""

# 定义参与模拟仿真的所有 Agent 角色类型列表
AGENT_ROLES = [
    "planner",    # 规划智能体：负责拆解任务、制定研究步骤与大纲
    "search",     # 搜索智能体：负责调用 web_search 检索互联网资料，处理工具调用生命周期
    "analysis",   # 分析智能体：整合检索数据，提取核心见解、完成定性/定量分析
    "writer",     # 撰写智能体：将分析结果组织成文，生成 Markdown 格式的正式初稿报告
    "reviewer",   # 评审智能体：审核初稿质量，指出缺陷以触发重试，或最终决定发表报告
]
