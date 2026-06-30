function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function renderInline(text) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
}

function flushParagraph(blocks, paragraph) {
  if (!paragraph.length) return
  blocks.push({
    type: 'paragraph',
    html: paragraph.map((line) => renderInline(line)).join('<br />')
  })
  paragraph.length = 0
}

function flushList(blocks, listItems) {
  if (!listItems.length) return
  blocks.push({
    type: 'list',
    items: listItems.map((item) => renderInline(item))
  })
  listItems.length = 0
}

function flushCode(blocks, codeLines, language) {
  if (!codeLines.length) return
  blocks.push({
    type: 'code',
    language,
    text: codeLines.join('\n')
  })
  codeLines.length = 0
}

function flushTable(blocks, tableRows) {
  if (!tableRows.length) return
  const cleanRows = tableRows.filter(row => !row.every(cell => /^[:\s-]*$/.test(cell)))
  if (cleanRows.length === 0) {
    tableRows.length = 0
    return
  }
  const headers = cleanRows[0]
  const rows = cleanRows.slice(1)
  blocks.push({
    type: 'table',
    headers: headers.map(cell => renderInline(cell)),
    rows: rows.map(row => row.map(cell => renderInline(cell)))
  })
  tableRows.length = 0
}

export function parseMarkdownSections(content) {
  if (!String(content || '').trim()) return []
  const lines = String(content || '').replace(/\r\n/g, '\n').split('\n')
  const sections = []
  let current = { title: '内容', titleHtml: '内容', blocks: [] }
  const paragraph = []
  const listItems = []
  const codeLines = []
  const tableRows = []
  let inCode = false
  let codeLanguage = ''
  let isFirstLine = true

  const pushCurrent = () => {
    flushParagraph(current.blocks, paragraph)
    flushList(current.blocks, listItems)
    flushCode(current.blocks, codeLines, codeLanguage)
    flushTable(current.blocks, tableRows)
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()

    // Skip empty lines at the very beginning of the document
    if (isFirstLine && !line.trim()) {
      continue
    }

    if (line.startsWith('```')) {
      isFirstLine = false
      if (inCode) {
        flushParagraph(current.blocks, paragraph)
        flushList(current.blocks, listItems)
        inCode = false
        flushCode(current.blocks, codeLines, codeLanguage)
        codeLanguage = ''
      } else {
        flushParagraph(current.blocks, paragraph)
        flushList(current.blocks, listItems)
        flushTable(current.blocks, tableRows)
        inCode = true
        codeLanguage = line.slice(3).trim()
      }
      continue
    }

    if (inCode) {
      codeLines.push(rawLine)
      continue
    }

    // Check for horizontal rule divider
    const isHr = /^[*-]{3,}$/.test(line.trim())
    if (isHr) {
      isFirstLine = false
      pushCurrent()
      current.blocks.push({
        type: 'hr'
      })
      continue
    }

    const isTableRow = line.startsWith('|') && line.endsWith('|')
    if (isTableRow) {
      isFirstLine = false
      flushParagraph(current.blocks, paragraph)
      flushList(current.blocks, listItems)
      flushCode(current.blocks, codeLines, codeLanguage)
      
      const cells = line.split('|').slice(1, -1).map(c => c.trim())
      tableRows.push(cells)
      continue
    } else {
      flushTable(current.blocks, tableRows)
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      isFirstLine = false
      pushCurrent()
      if (current.blocks.length || current.title !== '内容') {
        sections.push(current)
      }
      const rawTitle = heading[2].trim()
      current = {
        title: rawTitle,
        titleHtml: renderInline(rawTitle),
        blocks: []
      }
      continue
    }

    const bullet = line.match(/^\s*[-*]\s+(.+)$/)
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/)
    if (bullet || ordered) {
      isFirstLine = false
      flushParagraph(current.blocks, paragraph)
      listItems.push((bullet || ordered)[1].trim())
      continue
    }

    if (!line.trim()) {
      flushParagraph(current.blocks, paragraph)
      flushList(current.blocks, listItems)
      continue
    }

    // First line title auto-detection (when no markdown heading is present)
    if (isFirstLine && current.title === '内容') {
      const rawTitle = line.trim()
      current.title = rawTitle
      current.titleHtml = renderInline(rawTitle)
      isFirstLine = false
      continue
    }

    isFirstLine = false
    paragraph.push(line.trim())
  }

  pushCurrent()
  if (current.blocks.length || current.title !== '内容') {
    sections.push(current)
  }

  return sections.length ? sections : [{ title: '内容', titleHtml: '内容', blocks: [] }]
}

export function excerptMarkdown(content, limit = 160) {
  const plain = String(content || '')
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/#{1,6}\s+/g, '')
    .replace(/[*_`>\-\d.]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return plain.slice(0, limit)
}
