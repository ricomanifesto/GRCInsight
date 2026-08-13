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

  function renderInlineText(value) {
    let html = escapeHtml(value);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    return html;
  }

  function extractMarkdownLinks(value) {
    const source = String(value);
    const links = [];
    let markdown = '';
    let cursor = 0;
    while (cursor < source.length) {
      const labelStart = source.indexOf('[', cursor);
      if (labelStart < 0) {
        markdown += source.slice(cursor);
        break;
      }
      const labelEnd = source.indexOf(']', labelStart + 1);
      if (labelEnd < 0) {
        markdown += source.slice(cursor);
        break;
      }
      if (source[labelEnd + 1] !== '(') {
        markdown += source.slice(cursor, labelStart + 1);
        cursor = labelStart + 1;
        continue;
      }
      const destinationStartMarker = labelEnd;

      let depth = 1;
      let escaped = false;
      let destinationEnd = -1;
      for (let index = destinationStartMarker + 2; index < source.length; index += 1) {
        const character = source[index];
        if (escaped) {
          escaped = false;
          continue;
        }
        if (character === '\\') {
          escaped = true;
          continue;
        }
        if (character === '(') depth += 1;
        if (character === ')') {
          depth -= 1;
          if (depth === 0) {
            destinationEnd = index;
            break;
          }
        }
      }
      if (destinationEnd < 0) {
        markdown += source.slice(cursor, destinationStartMarker + 2);
        cursor = destinationStartMarker + 2;
        continue;
      }

      const token = `@@GRCINSIGHT_LINK_${links.length}@@`;
      markdown += source.slice(cursor, labelStart) + token;
      links.push({
        token,
        text: source.slice(labelStart + 1, destinationStartMarker),
        url: source.slice(destinationStartMarker + 2, destinationEnd),
      });
      cursor = destinationEnd + 1;
    }
    return {
      markdown,
      restore(html) {
        links.forEach(link => {
          html = html.replace(
            link.token,
            renderMarkdownLink(renderInlineText(link.text), link.url),
          );
        });
        return html;
      },
    };
  }

  function renderInlineMarkdown(value) {
    const extracted = extractMarkdownLinks(value);
    return extracted.restore(renderInlineText(extracted.markdown));
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

    // Extract links before escaping the surrounding Markdown. Escaping first
    // turns query separators into &amp;, which would then be escaped a second
    // time when the URL is written into href.
    const extractedLinks = extractMarkdownLinks(md);
    let html = escapeHtml(extractedLinks.markdown);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    html = html.replace(/^####\s+(.*)$/gm, '<h4>$1</h4>');
    html = html.replace(/^###\s+(.*)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##\s+(.*)$/gm, '<h2>$1</h2>');
    html = html.replace(/^#\s+(.*)$/gm, '<h1>$1</h1>');
    // Tables run before HR so the separator row is not eaten by the HR rule.
    html = html.replace(/^(?:\|.+\|(?:\n|$)){2,}/gm, m => renderTable(m));
    html = html.replace(/^-{3,}[ \t]*$/gm, '<hr>');
    html = html.replace(/^_{3,}[ \t]*$/gm, '<hr>');
    html = html.replace(/^\*{3,}[ \t]*$/gm, '<hr>');
    html = html.replace(/^(?:&gt;\s?.*(?:\n|$))+/gm, m => `<blockquote>${m.replace(/^&gt;\s?/gm, '').trim()}</blockquote>`);
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
    // Restore links and fenced code blocks last so their content never affects
    // block parsing or receives a second escaping pass.
    html = extractedLinks.restore(html);
    return html.replace(/%%CODEBLOCK_(\d+)%%/g, (_, i) => `<pre><code>${escapeHtml(codeBlocks[+i])}</code></pre>`);
  }

  const metadataLabels = {
    'generated': 'Generated',
    'date of issue': 'Date of issue',
    'analysis period': 'Analysis period',
    'source': 'Source',
    'total articles analyzed': 'Articles analyzed',
    'articles analyzed': 'Articles analyzed',
    'grc-relevant articles': 'GRC-relevant articles',
    'model': 'Model',
    'analysis mode': 'Analysis mode',
  };

  const metadataOrder = [
    'generated',
    'date of issue',
    'analysis period',
    'source',
    'articles analyzed',
    'grc-relevant articles',
    'model',
    'analysis mode',
  ];

  function parseReportDocument(markdown) {
    const normalized = normalizeReportMarkdown(String(markdown || ''));
    const lines = normalized.split('\n');
    let title = '';
    const metadata = {};
    let bodyStart = lines.length;

    lines.forEach((line, index) => {
      if (bodyStart !== lines.length) return;
      if (!title && /^#\s+/.test(line)) {
        title = line.replace(/^#\s+/, '').trim();
        return;
      }
      if (/^##\s+/.test(line)) {
        bodyStart = index;
        return;
      }

      const standard = line.match(/^\*\*([^*]+?):\*\*\s*(.+?)\s*$/);
      const legacy = line.match(/^\*\*([^*]+?):\s*(.+?)\*\*\s*$/);
      const match = standard || legacy;
      if (!match) return;
      const key = match[1].trim().toLowerCase();
      if (metadataLabels[key]) metadata[key] = match[2].trim();
    });

    if (metadata['total articles analyzed'] && !metadata['articles analyzed']) {
      metadata['articles analyzed'] = metadata['total articles analyzed'];
    }

    return {
      title,
      metadata,
      bodyMarkdown: lines.slice(bodyStart).join('\n').trim(),
    };
  }

  function renderReportMetadata(metadata) {
    const items = metadataOrder
      .filter(key => metadata[key])
      .map(key => `<div class="report-meta-item"><dt>${metadataLabels[key]}</dt><dd>${renderInlineMarkdown(metadata[key])}</dd></div>`)
      .join('');
    if (!items) return '';
    return `<section class="card report-provenance"><h2>About this report</h2><dl class="report-meta">${items}</dl></section>`;
  }

  function renderReportSections(markdown) {
    const html = renderMarkdown(markdown);
    return html
      .split(/(?=<h2>)/)
      .map(part => part.replace(/^\s*(?:<hr>\s*)+/, '').replace(/(?:\s*<hr>)+\s*$/, '').trim())
      .filter(Boolean)
      .map(part => `<section class="card">${part}</section>`)
      .join('');
  }

  function renderReportDocument(markdown) {
    const report = parseReportDocument(markdown);
    return renderReportMetadata(report.metadata) + renderReportSections(report.bodyMarkdown);
  }

  window.GRCInsightRenderer = {
    escapeHtml,
    escapeAttribute,
    sanitizeMarkdownUrl,
    renderMarkdownLink,
    renderInlineMarkdown,
    normalizeReportMarkdown,
    renderMarkdown,
    parseReportDocument,
    renderReportDocument,
  };
})();
