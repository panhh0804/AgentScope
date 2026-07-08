export function lineOption(title, xData, series) {
  return {
    tooltip: { trigger: 'axis' },
    grid: { top: 18, right: 18, bottom: 28, left: 44 },
    xAxis: {
      type: 'category',
      data: xData,
      boundaryGap: false,
      axisLabel: { color: '#9bc0d9' },
      axisLine: { lineStyle: { color: '#3f5a70' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9bc0d9' },
      axisLine: { lineStyle: { color: '#3f5a70' } },
      splitLine: { lineStyle: { color: 'rgba(139, 192, 217, 0.12)' } }
    },
    series: series.map((item) => ({
      symbol: 'none',
      showSymbol: false,
      hoverAnimation: false,
      ...item
    }))
  }
}

export function barOption(title, xData, data, name) {
  return {
    title: { text: title, textStyle: { fontSize: 14, fontWeight: 600, color: '#dbe7f3' } },
    tooltip: { trigger: 'axis' },
    grid: { top: 46, right: 18, bottom: 42, left: 52 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { rotate: 20, color: '#9bc0d9' },
      axisLine: { lineStyle: { color: '#3f5a70' } }
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9bc0d9' },
      axisLine: { lineStyle: { color: '#3f5a70' } },
      splitLine: { lineStyle: { color: 'rgba(139, 192, 217, 0.12)' } }
    },
    series: [{ name, type: 'bar', data, itemStyle: { color: '#3b82f6' } }]
  }
}

export function graphOption(graph) {
  const nodes = (graph.nodes || []).map((node) => ({
    ...node,
    symbolSize: Math.max(36, Math.min(82, Number(node.value || node.symbolSize || 36))),
    itemStyle: { color: '#06b6d4' }
  }))
  const links = (graph.links || []).map((link) => ({
    ...link,
    lineStyle: {
      color: 'rgba(103, 232, 249, 0.55)',
      curveness: 0.16,
      width: Math.max(1, Math.min(8, Number(link.call_count || 1) / 150))
    }
  }))
  return {
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params) => {
        if (params.dataType === 'node') {
          return `节点: <b>${params.name}</b><br/>交互数: ${params.value ?? 0}`
        }
        const link = params.data || {}
        return `协作流动: <b>${link.source} ➔ ${link.target}</b><br/>交互次数: ${link.call_count ?? 0}<br/>平均时延: ${link.avg_latency_ms ?? 0} ms<br/>失败次数: ${link.failed_count ?? 0}`
      }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        draggable: true,
        top: 24,
        right: 28,
        bottom: 30,
        left: 28,
        symbol: 'circle',
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [4, 9],
        label: { show: true, position: 'bottom', color: '#bdefff', fontSize: 10, fontWeight: 'bold' },
        force: { repulsion: 360, edgeLength: [170, 240], gravity: 0.035 },
        data: nodes,
        links
      }
    ]
  }
}
