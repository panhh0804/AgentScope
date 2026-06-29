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
    series: [{ name, type: 'bar', data, itemStyle: { color: '#6366f1' } }]
  }
}

export function graphOption(graph) {
  return {
    tooltip: {},
    series: [
      {
        type: 'graph',
        layout: 'force',
        roam: true,
        label: { show: true, color: '#f8fafc', fontSize: 11 },
        force: { repulsion: 240, edgeLength: 130 },
        data: (graph.nodes || []).map((node) => ({
          ...node,
          symbolSize: Math.max(36, Math.min(82, node.value || 36)),
          itemStyle: { color: '#06b6d4' }
        })),
        links: (graph.links || []).map((link) => ({
          ...link,
          lineStyle: { width: Math.max(1, Math.min(8, (link.call_count || 1) / 150)), color: 'rgba(103, 232, 249, 0.35)' }
        }))
      }
    ]
  }
}
