(function () {
  // Canonical rendering contract for the GRC report. One module owns the
  // Markdown -> HTML transform and URL sanitization; the page controller and
  // the Node renderer check both consume these exports and nothing else.

  function escapeHtml(s) {
    return String(s).replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
  }

  function escapeAttribute(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
  }

  function sanitizeMarkdownUrl(url) {
    const value = String(url).trim();
    if (!value || /[\s"'<>]/.test(value)) return null;
    if (/^(https?:\/\/|\/(?!\/)|\.{0,2}\/|#)/i.test(value)) return value;
    if (!/^[a-z][a-z0-9+.-]*:/i.test(value)) return value;
    return null;
  }

  function renderMarkdownLink(text, url) {
    const safeUrl = sanitizeMarkdownUrl(url);
    if (!safeUrl) return text;
    return `<a href="${escapeAttribute(safeUrl)}" target="_blank" rel="noopener">${text}</a>`;
  }

  // Reports are sometimes generated with numbered section headers ("1. Executive
  // Summary") instead of Markdown h2. Promote the known section labels to h2 so
  // the page treats them as top-level sections; leave numbered prose untouched.
  function normalizeReportMarkdown(markdown) {
    if (typeof markdown !== 'string') return markdown;
    const expectedSectionTitles = new Set([
      'Executive Summary',
      'Key Regulatory Developments',
      'Industry Impact Analysis',
      'Threat Actor Activities',
      'CVE and Vulnerability Highlights',
      'Risk Assessment',
      'Recommendations for Action',
      'Source Highlights',
    ]);
    return markdown.replace(/^\d{1,2}[\).]\s+([^\n]+)$/gm, (line, title) => {
      const normalizedTitle = title.trim();
      return expectedSectionTitles.has(normalizedTitle) ? `## ${normalizedTitle}` : line;
    });
  }

  function renderTable(block) {
    const rows = block.trim().split('\n').filter(r => r.trim());
    if (rows.length < 2) return block;
    const parseRow = r => r.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
    const headers = parseRow(rows[0]);
    const isSeparator = rows[1] && /^\s*\|?[\s\-:|]+\|?\s*$/.test(rows[1]);
    const startIdx = isSeparator ? 2 : 1;
    let html = '<div class="table-wrap"><table><thead><tr>';
    headers.forEach(h => { html += `<th>${h}</th>`; });
    html += '</tr></thead><tbody>';
    for (let i = startIdx; i < rows.length; i++) {
      html += '<tr>';
      parseRow(rows[i]).forEach(c => { html += `<td>${c}</td>`; });
      html += '</tr>';
    }
    return html + '</tbody></table></div>';
  }

  function renderNestedList(block) {
    const lines = block.trim().split(/\n/).filter(l => /^\s*-\s+/.test(l));
    let html = '';
    let level = 0;
    const open = n => { for (let i = 0; i < n; i++) html += '<ul>'; };
    const close = n => { for (let i = 0; i < n; i++) html += '</ul>'; };
    lines.forEach((line, idx) => {
      const m = line.match(/^(\s*)-\s+(.*)$/);
      const indent = Math.floor((m[1] || '').length / 2) + 1; // 2 spaces per level, base 1
      if (idx === 0) { open(indent); level = indent; }
      else if (indent > level) { open(indent - level); level = indent; }
      else if (indent < level) { close(level - indent); level = indent; }
      html += `<li>${m[2]}</li>`;
    });
    close(level);
    return html;
  }

  // Pure Markdown -> HTML for the report body. No DOM access, so the same
  // function renders in the browser and under the Node renderer check.
  function renderMarkdown(md) {
    md = normalizeReportMarkdown(md);

    // Pull fenced code blocks out before escaping, restore them afterwards.
    const codeBlocks = [];
    md = md.replace(/^```[\s\S]*?^```/gm, m => {
      codeBlocks.push(m.replace(/^```\w*\n?/, '').replace(/\n?```$/, ''));
      return `%%CODEBLOCK_${codeBlocks.length - 1}%%`;
    });

    let html = escapeHtml(md);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/^####\s+(.*)$/gm, '<h4>$1</h4>');
    html = html.replace(/^###\s+(.*)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##\s+(.*)$/gm, '<h2>$1</h2>');
    html = html.replace(/^#\s+(.*)$/gm, '<h1>$1</h1>');
    // Tables run before HR so the separator row is not eaten by the HR rule.
    html = html.replace(/^(?:\|.+\|(?:\n|$)){2,}/gm, m => renderTable(m));
    html = html.replace(/^-{3,}$/gm, '<hr>');
    html = html.replace(/^_{3,}$/gm, '<hr>');
    html = html.replace(/^\*{3,}$/gm, '<hr>');
    html = html.replace(/^(?:&gt;\s?.*(?:\n|$))+/gm, m => `<blockquote>${m.replace(/^&gt;\s?/gm, '').trim()}</blockquote>`);
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, text, url) => renderMarkdownLink(text, url));
    // Leading indent is horizontal whitespace only ([ \t]*, not \s*) so the
    // pattern never reaches across the blank line that precedes a list.
    html = html.replace(/^(?:[ \t]*-\s+.*(?:\n|$))+/gm, m => renderNestedList(m));
    html = html.replace(/^(?:\d+\.\s+.*(?:\n|$))+/gm, m => {
      const items = m.trim().split(/\n/).filter(l => /^\d+\.\s+/.test(l));
      return '<ol>' + items.map(l => `<li>${l.replace(/^\d+\.\s+/, '')}</li>`).join('') + '</ol>';
    });
    // Assemble paragraphs line by line rather than by blank-line splitting.
    // Each block construct above consumes the newline that ended its last line,
    // which can collapse the blank line separating it from an adjacent
    // paragraph; grouping by line keeps that paragraph in its own <p> instead
    // of leaking it out as loose inline nodes. Block-level lines (and the
    // single-line code-block placeholders) pass through untouched.
    const blockLine = /^\s*(?:<(?:h\d|ul|ol|li|table|div|hr|pre|blockquote)|%%CODEBLOCK_\d+%%)/;
    const assembled = [];
    let paragraph = [];
    const flushParagraph = () => {
      if (!paragraph.length) return;
      const text = paragraph.join('\n').trim();
      if (text) assembled.push(`<p>${text}</p>`);
      paragraph = [];
    };
    html.split('\n').forEach(line => {
      if (!line.trim()) { flushParagraph(); return; }
      if (blockLine.test(line)) { flushParagraph(); assembled.push(line); return; }
      paragraph.push(line);
    });
    flushParagraph();
    html = assembled.join('\n');
    // Restore fenced code blocks last so their internal newlines never affect
    // paragraph assembly.
    return html.replace(/%%CODEBLOCK_(\d+)%%/g, (_, i) => `<pre><code>${escapeHtml(codeBlocks[+i])}</code></pre>`);
  }

  window.GRCInsightRenderer = {
    escapeHtml,
    escapeAttribute,
    sanitizeMarkdownUrl,
    renderMarkdownLink,
    normalizeReportMarkdown,
    renderMarkdown,
  };
})();
