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

export function parseMarkdownSections(content) {
  if (!String(content || '').trim()) return []
  const lines = String(content || '').replace(/\r\n/g, '\n').split('\n')
  const sections = []
  let current = { title: '内容', blocks: [] }
  const paragraph = []
  const listItems = []
  const codeLines = []
  let inCode = false
  let codeLanguage = ''

  const pushCurrent = () => {
    flushParagraph(current.blocks, paragraph)
    flushList(current.blocks, listItems)
    flushCode(current.blocks, codeLines, codeLanguage)
  }

  for (const rawLine of lines) {
    const line = rawLine.trimEnd()

    if (line.startsWith('```')) {
      if (inCode) {
        flushParagraph(current.blocks, paragraph)
        flushList(current.blocks, listItems)
        inCode = false
        flushCode(current.blocks, codeLines, codeLanguage)
        codeLanguage = ''
      } else {
        flushParagraph(current.blocks, paragraph)
        flushList(current.blocks, listItems)
        inCode = true
        codeLanguage = line.slice(3).trim()
      }
      continue
    }

    if (inCode) {
      codeLines.push(rawLine)
      continue
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/)
    if (heading) {
      pushCurrent()
      if (current.blocks.length || current.title !== '内容') {
        sections.push(current)
      }
      current = {
        title: heading[2].trim(),
        blocks: []
      }
      continue
    }

    const bullet = line.match(/^\s*[-*]\s+(.+)$/)
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/)
    if (bullet || ordered) {
      flushParagraph(current.blocks, paragraph)
      listItems.push((bullet || ordered)[1].trim())
      continue
    }

    if (!line.trim()) {
      flushParagraph(current.blocks, paragraph)
      flushList(current.blocks, listItems)
      continue
    }

    paragraph.push(line.trim())
  }

  pushCurrent()
  if (current.blocks.length || current.title !== '内容') {
    sections.push(current)
  }

  return sections.length ? sections : [{ title: '内容', blocks: [] }]
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
