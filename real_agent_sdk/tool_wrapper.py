from __future__ import annotations

from typing import Dict, List


class SearchTool:
    name = "local_research_search"

    def call(self, query: str) -> Dict:
        # Deterministic local tool for instrumentation. It keeps the SDK runnable
        # when no external search service is available.
        snippets: List[str] = [
            "教育行业关注个性化学习、教师备课减负、学习过程评价和智能答疑。",
            "大模型应用落地时需要关注数据安全、内容准确性、成本控制和教师监督。",
            "多 Agent 工作流适合将规划、检索、写作和审核拆分为可观测步骤。",
        ]
        return {
            "query": query,
            "results": snippets,
            "summary": "；".join(snippets),
        }

