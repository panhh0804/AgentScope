export function lineOption(title, xData, series) {
  return {
    title: { text: title, textStyle: { fontSize: 14, fontWeight: 600 } },
    tooltip: { trigger: 'axis' },
    grid: { top: 46, right: 18, bottom: 32, left: 44 },
    xAxis: { type: 'category', data: xData, boundaryGap: false },
    yAxis: { type: 'value' },
    series
  }
}

export function barOption(title, xData, data, name) {
  return {
    title: { text: title, textStyle: { fontSize: 14, fontWeight: 600 } },
    tooltip: { trigger: 'axis' },
    grid: { top: 46, right: 18, bottom: 42, left: 52 },
    xAxis: { type: 'category', data: xData, axisLabel: { rotate: 20 } },
    yAxis: { type: 'value' },
    series: [{ name, type: 'bar', data, itemStyle: { color: '#2563eb' } }]
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
        label: { show: true },
        force: { repulsion: 240, edgeLength: 130 },
        data: (graph.nodes || []).map((node) => ({
          ...node,
          symbolSize: Math.max(36, Math.min(82, node.value || 36)),
          itemStyle: { color: '#2563eb' }
        })),
        links: (graph.links || []).map((link) => ({
          ...link,
          lineStyle: { width: Math.max(1, Math.min(8, (link.call_count || 1) / 150)), color: '#64748b' }
        }))
      }
    ]
  }
}

