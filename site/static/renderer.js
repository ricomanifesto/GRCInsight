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

  function decodeMarkdownEscapes(value) {
    return String(value).replace(/\\([\\\[\]()|])/g, '$1');
  }

  function sanitizeMarkdownUrl(url) {
    const value = decodeMarkdownEscapes(url).trim();
    if (!value || /[\s"<>]/.test(value)) return null;
    if (/^(https?:\/\/|\/(?!\/)|\.{0,2}\/|#)/i.test(value)) return value;
    if (!/^[a-z][a-z0-9+.-]*:/i.test(value)) return value;
    return null;
  }

  function renderMarkdownLink(text, url) {
    const safeUrl = sanitizeMarkdownUrl(url);
    if (!safeUrl) return text;
    const className = text === 'View in SentryDigest' ? ' class="digest-handoff"' : '';
    return `<a${className} href="${escapeAttribute(safeUrl)}" target="_blank" rel="noopener">${text}</a>`;
  }

  function renderInlineText(value) {
    const decoded = decodeMarkdownEscapes(value);
    let html = escapeHtml(decoded);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    return html;
  }

  function renderLinkLabel(value) {
    return escapeHtml(decodeMarkdownEscapes(value));
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
      let labelDepth = 1;
      let labelEscaped = false;
      let labelEnd = -1;
      for (let index = labelStart + 1; index < source.length; index += 1) {
        const character = source[index];
        if (labelEscaped) {
          labelEscaped = false;
          continue;
        }
        if (character === '\\') {
          labelEscaped = true;
          continue;
        }
        if (character === '[') labelDepth += 1;
        if (character === ']') {
          labelDepth -= 1;
          if (labelDepth === 0) {
            labelEnd = index;
            break;
          }
        }
      }
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
        position: labelStart,
        text: source.slice(labelStart + 1, destinationStartMarker),
        url: source.slice(destinationStartMarker + 2, destinationEnd),
      });
      cursor = destinationEnd + 1;
    }
    return {
      markdown,
      links,
      restore(html, renderLink = link => renderMarkdownLink(renderLinkLabel(link.text), link.url)) {
        if (!links.length) return html;
        // Render in link order (citation numbering follows call order), then
        // substitute every token in one pass instead of rescanning the whole
        // document once per link. Each token is replaced at most once, and the
        // rendered link is inserted literally.
        const rendered = links.map(link => renderLink(link));
        const pending = new Set(rendered.keys());
        return html.replace(/@@GRCINSIGHT_LINK_(\d+)@@/g, (token, index) => {
          const position = Number(index);
          if (!pending.delete(position)) return token;
          return rendered[position];
        });
      },
    };
  }

  function renderInlineMarkdown(value) {
    const extracted = extractMarkdownLinks(value);
    return extracted.restore(renderInlineText(extracted.markdown));
  }

  function renderEvidenceAffordances(html) {
    const evidence = '<span class="evidence-label">Evidence</span>';
    html = html.replace(
      /<p>((?:(?!<\/p>)[\s\S])*?)\s*<strong>Evidence:<\/strong>\s*([\s\S]*?)<\/p>/g,
      (_match, claim, links) => `<p>${claim.trim()}</p><aside class="evidence-note" aria-label="Evidence">${evidence}${links.trim()}</aside>`,
    );
    html = html.replace(
      /<li>((?:(?!<\/li>)[\s\S])*?)\s*<strong>Evidence:<\/strong>\s*([\s\S]*?)<\/li>/g,
      (_match, claim, links) => `<li>${claim.trim()}<aside class="evidence-note" aria-label="Evidence">${evidence}${links.trim()}</aside></li>`,
    );
    html = html.replace(
      /<td>((?:(?!<\/td>)[\s\S])*?)\s*<strong>Evidence:<\/strong>\s*([\s\S]*?)<\/td>/g,
      (_match, claim, links) => `<td>${claim.trim()}<div class="evidence-inline">${evidence}${links.trim()}</div></td>`,
    );
    return html;
  }

  // Reports are sometimes generated with numbered section headers ("1. Executive
  // Summary") instead of Markdown h2. Promote the known section labels to h2 so
  // the page treats them as top-level sections; leave numbered prose untouched.
  function normalizeReportMarkdown(markdown) {
    if (typeof markdown !== 'string') return markdown;
    const expectedSectionTitles = new Set([
      'Executive Summary',
      'Key Regulatory Developments',
      'Sourced Regulatory Changes',
      'Evidence and Decisions',
      'Inferred Control and Governance Implications',
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

  function renderOrderedLists(markdown) {
    const lines = markdown.split('\n');
    const output = [];
    let index = 0;

    while (index < lines.length) {
      const firstItem = lines[index].match(/^\d+\.\s+(.*)$/);
      if (!firstItem) {
        output.push(lines[index]);
        index += 1;
        continue;
      }

      const items = [];
      while (index < lines.length) {
        const item = lines[index].match(/^\d+\.\s+(.*)$/);
        if (!item) break;

        items.push(item[1]);
        index += 1;

        // A blank line makes a Markdown list "loose"; it does not end the
        // list when the next non-blank line is another numbered item.
        let nextItem = index;
        while (nextItem < lines.length && !lines[nextItem].trim()) nextItem += 1;
        if (nextItem < lines.length && /^\d+\.\s+/.test(lines[nextItem])) {
          index = nextItem;
        }
      }

      output.push('<ol>' + items.map(item => `<li>${item}</li>`).join('') + '</ol>');
    }

    return output.join('\n');
  }

  // Pure Markdown -> HTML for the report body. No DOM access, so the same
  // function renders in the browser and under the Node renderer check.
  function renderMarkdown(md, compactCitations = false) {
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
    const renderLink = compactCitations ? citationRenderer(md, extractedLinks.links) : undefined;
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
    html = renderOrderedLists(html);
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
    // Bounded numeric references emitted for literal quoted evidence. Restore
    // after Markdown parsing, before links/code: do not alter their identities.
    html = html.replace(/&amp;#(33|35|37|38|40|41|42|60|62|64|91|92|93|95|96|124);/g, '&#$1;');
    html = extractedLinks.restore(html, renderLink);
    html = renderEvidenceAffordances(html);
    html = html.replace(/%%CODEBLOCK_(\d+)%%/g, (_, i) => `<pre><code>${escapeHtml(codeBlocks[+i])}</code></pre>`);
    return html;
  }

  const metadataLabels = {
    'generated': 'Generated',
    'date of issue': 'Date of issue',
    'analysis period': 'Analysis period',
    'source': 'Source',
    'source issue': 'Source issue',
    'total articles analyzed': 'Articles analyzed',
    'articles analyzed': 'Articles analyzed',
    'grc-relevant articles': 'GRC-relevant articles',
    'authoring model': 'Authoring model',
    'requested route': 'Requested route',
    'model': 'Model',
    'analysis mode': 'Analysis mode',
  };

  const metadataOrder = [
    'generated',
    'date of issue',
    'analysis period',
    'source',
    'source issue',
    'articles analyzed',
    'grc-relevant articles',
    'authoring model',
    'requested route',
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

  function renderGeneratedTimestamp(value) {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return renderInlineMarkdown(value);

    const months = [
      'January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December',
    ];
    const hours = parsed.getUTCHours();
    const minutes = String(parsed.getUTCMinutes()).padStart(2, '0');
    const meridiem = hours >= 12 ? 'PM' : 'AM';
    const displayHour = hours % 12 || 12;
    const display = `${months[parsed.getUTCMonth()]} ${parsed.getUTCDate()}, ${parsed.getUTCFullYear()} at ${displayHour}:${minutes} ${meridiem} UTC`;
    return `<time datetime="${escapeAttribute(value)}">${display}</time>`;
  }

  function renderReportMetadata(metadata) {
    const metadataItems = metadataOrder
      .filter(key => metadata[key])
      .map(key => {
        const value = key === 'generated'
          ? renderGeneratedTimestamp(metadata[key])
          : renderInlineMarkdown(metadata[key]);
        return `<div class="report-meta-item"><dt>${metadataLabels[key]}</dt><dd>${value}</dd></div>`;
      })
      .join('');
    const manifestItem = '<div class="report-meta-item report-meta-evidence"><dt>Evidence manifest</dt><dd><a class="manifest-link" href="evidence-manifest.json" target="_blank" rel="noopener">Machine-readable JSON</a></dd></div>';
    const requestedRoute = String(metadata['requested route'] || '').trim().toLowerCase();
    const routedByAlias = /(?:^|\/)openrouter\/(?:free|auto)$/.test(requestedRoute);
    const routeMeaning = routedByAlias
      ? 'routing alias selected for the run'
      : 'model route configured for the run';
    const modelExplanation = requestedRoute && metadata['authoring model']
      ? `<p class="provenance-explanation">The requested route is the OpenRouter ${routeMeaning}; the authoring model is the upstream model attested with the completed report.</p>`
      : '';
    if (!metadataItems) return '';
    return `<section class="card report-provenance"><h2>About this report</h2><dl class="report-meta">${metadataItems}${manifestItem}</dl>${modelExplanation}</section>`;
  }

  function citationRenderer(markdown, links) {
    const sourceSection = /^## Source Highlights\s*$/m.exec(markdown);
    const sourceStart = sourceSection ? sourceSection.index : markdown.length;
    const followingSection = markdown.slice(sourceStart + (sourceSection?.[0].length || 0)).search(/^## /m);
    const sourceEnd = followingSection < 0 ? markdown.length : sourceStart + sourceSection[0].length + followingSection;
    const registry = new Map();
    const eligible = link => /^https?:\/\//i.test(link.url) && sanitizeMarkdownUrl(link.url) && decodeMarkdownEscapes(link.text) !== 'View in SentryDigest';
    const isHighlight = link => link.position >= sourceStart && link.position < sourceEnd;
    const sourceIdentity = link => JSON.stringify([sanitizeMarkdownUrl(link.url), decodeMarkdownEscapes(link.text)]);
    links.filter(isHighlight).forEach(link => {
      const identity = sourceIdentity(link);
      if (eligible(link) && !registry.has(identity)) registry.set(identity, { number: registry.size + 1 });
    });
    const highlighted = new Set();
    return link => {
      const url = sanitizeMarkdownUrl(link.url);
      const identity = sourceIdentity(link);
      const citation = eligible(link) && registry.get(identity);
      if (!citation) return renderMarkdownLink(renderLinkLabel(link.text), link.url);
      const number = citation.number;
      if (isHighlight(link)) {
        const marker = highlighted.has(identity) ? '' : `<span class="source-number" id="source-${number}">[${number}]</span> `;
        highlighted.add(identity);
        return marker + renderMarkdownLink(renderLinkLabel(link.text), link.url);
      }
      const title = decodeMarkdownEscapes(link.text);
      return `<a class="report-citation" href="${escapeAttribute(url)}" aria-label="${escapeAttribute(`Source ${number}: ${title}`)}" title="${escapeAttribute(title)}" target="_blank" rel="noopener">[${number}]</a>`;
    };
  }

  // Application-owned control catalog, in report order. Coverage shows every
  // area, including the ones without a finding this period.
  const CONTROL_AREAS = [
    'Access management',
    'Vulnerability management',
    'Incident response',
    'Third-party risk',
    'Data protection',
    'Change management',
    'Monitoring and detection',
    'Governance and accountability',
  ];
  const PRIORITY_LEVELS = ['High', 'Medium', 'Low'];
  const FINDING_FIELDS = [
    'Review priority',
    'Why it matters',
    'Source evidence',
    'Evidence to request',
    'Decision trigger',
    'Reference controls',
  ];

  function pad(number) {
    return String(number).padStart(2, '0');
  }

  function markdownSection(markdown, name) {
    const match = new RegExp(`^## ${name}\\s*$([\\s\\S]*?)(?=^## |(?![\\s\\S]))`, 'm').exec(markdown);
    return match ? match[1] : '';
  }

  function reportStatistics(markdown, rows) {
    const regulatory = markdownSection(markdown, 'Sourced Regulatory Changes')
      .split('\n').filter(line => /^\|/.test(line.trim())).slice(2).length;
    const sources = markdownSection(markdown, 'Source Highlights')
      .split('\n').filter(line => /^\s*-\s+\[/.test(line)).length;
    return {
      findings: rows.length,
      high: rows.filter(row => row.priority === 'High').length,
      areas: new Set(rows.map(row => row.control)).size,
      regulatory,
      sources,
    };
  }

  function renderGlance(stats) {
    const items = [
      ['Findings', stats.findings],
      ['High priority', stats.high],
      ['Control areas', stats.areas],
      ['Regulatory changes', stats.regulatory],
      ['Sources reviewed', stats.sources],
    ];
    return `<dl class="glance" aria-label="Report at a glance">${items.map(([label, value]) =>
      `<div class="glance-item"><dt class="glance-label">${label}</dt><dd class="glance-value">${value}</dd></div>`
    ).join('')}</dl>`;
  }

  // Split rendered paragraph HTML after its first sentence, skipping initials
  // and common abbreviations so "U.S." does not end a lead early.
  function splitLead(html) {
    const boundary = /[.!?](?=\s+(?:[A-Z0-9“"(]|<a\b))/g;
    let match;
    while ((match = boundary.exec(html))) {
      const before = html.slice(0, match.index);
      if (before.lastIndexOf('<') > before.lastIndexOf('>')) continue;
      const token = before.slice(before.search(/\S+$/));
      if (/^(?:[A-Za-z]\.)+[A-Za-z]$|^[A-Z]$|^(?:e\.g|i\.e|etc|vs|Inc|Corp|Ltd|Co|No|St)$/.test(token)) continue;
      return { lead: html.slice(0, match.index + 1), rest: html.slice(match.index + 1) };
    }
    return { lead: html, rest: '' };
  }

  function renderSummary(part, stats) {
    const heading = '<h2>Executive Summary</h2>';
    const body = part.slice(heading.length).trim();
    const paragraphs = body.match(/<p>[\s\S]*?<\/p>/g) || [];
    if (!paragraphs.length || body.replace(/<p>[\s\S]*?<\/p>/g, '').trim()) return part;
    const inner = paragraphs.map(paragraph => paragraph.slice(3, -4));
    const scopeIndex = inner.length > 1 && /^Scope:/.test(inner[inner.length - 1]) ? inner.length - 1 : -1;
    const messages = inner
      .filter((_text, index) => index !== scopeIndex)
      .map(text => {
        const { lead, rest } = splitLead(text);
        return `<li class="key-message"><p><strong class="key-lead">${lead}</strong>${rest}</p></li>`;
      });
    const scope = scopeIndex >= 0 ? `<p class="summary-scope">${inner[scopeIndex]}</p>` : '';
    return `${heading}${renderGlance(stats)}<h3 class="key-messages-title">Key messages</h3><ol class="key-messages">${messages.join('')}</ol>${scope}`;
  }

  function priorityTitle(stats) {
    if (stats.findings === 1) {
      return stats.high ? 'The one finding carries high review priority' : 'The one finding carries no high review priority';
    }
    if (stats.high === 0) return `None of the ${stats.findings} findings carries high review priority`;
    if (stats.high === stats.findings) return `All ${stats.findings} findings carry high review priority`;
    return `${stats.high} of ${stats.findings} findings carry high review priority`;
  }

  function coverageTitle(rows, stats) {
    const counts = new Map();
    rows.forEach(row => counts.set(row.control, (counts.get(row.control) || 0) + 1));
    const ranked = Array.from(counts).sort((a, b) => b[1] - a[1]);
    let title = `Findings span ${stats.areas} of ${CONTROL_AREAS.length} control areas`;
    if (ranked.length && ranked[0][1] > 1 && (ranked.length === 1 || ranked[0][1] > ranked[1][1])) {
      title += `; ${ranked[0][0].toLowerCase()} has the most, with ${ranked[0][1]}`;
    }
    return title;
  }

  function renderOverview(rows, stats) {
    const findingRows = rows.map((row, index) => {
      const level = row.priority.toLowerCase();
      const title = escapeHtml(row.headline || row.focus);
      return `<tr class="priority-${level}"><td><span class="finding-index">${pad(index + 1)}</span></td>` +
        `<td class="finding-cell"><a href="#finding-${index + 1}">${title}</a></td>` +
        `<td>${escapeHtml(row.control)}</td>` +
        `<td><span class="priority-pill"><span class="sr-only">Review priority: </span>${escapeHtml(row.priority)}</span></td>` +
        `<td>${row.owner ? escapeHtml(row.owner) : ''}</td></tr>`;
    }).join('');
    const findingsExhibit = `<figure class="exhibit"><p class="exhibit-label">Exhibit 1</p>` +
      `<h3 class="exhibit-title">${escapeHtml(priorityTitle(stats))}</h3>` +
      `<div class="exhibit-table"><table class="findings-table"><thead><tr><th scope="col">No.</th><th scope="col">Finding</th><th scope="col">Control area</th><th scope="col">Priority</th><th scope="col">Owner</th></tr></thead><tbody>${findingRows}</tbody></table></div>` +
      `<figcaption class="exhibit-note">Inferred review priorities rank what to check first; they come from the quoted evidence and are not measured risk. Select a finding to read its evidence and decision.</figcaption></figure>`;

    const cells = new Map();
    rows.forEach(row => {
      const key = `${row.control}|${row.priority}`;
      cells.set(key, (cells.get(key) || 0) + 1);
    });
    const coverageRows = CONTROL_AREAS.map(area => {
      const counts = PRIORITY_LEVELS.map(level => cells.get(`${area}|${level}`) || 0);
      const total = counts.reduce((sum, count) => sum + count, 0);
      const tds = counts.map(count => count
        ? `<td class="coverage-cell level-${Math.min(count, 3)}">${count}</td>`
        : '<td class="coverage-cell is-empty"><span class="sr-only">None</span></td>').join('');
      return `<tr class="${total ? 'review-map-group' : 'is-quiet'}"><th scope="row">${escapeHtml(area)}</th>${tds}<td class="coverage-total">${total || '–'}</td></tr>`;
    }).join('');
    const coverageExhibit = `<figure class="exhibit exhibit-coverage"><p class="exhibit-label">Exhibit 2</p>` +
      `<h3 class="exhibit-title">${escapeHtml(coverageTitle(rows, stats))}</h3>` +
      `<div class="exhibit-table"><table class="coverage-table"><thead><tr><th scope="col">Control area</th>${PRIORITY_LEVELS.map(level => `<th scope="col">${level}</th>`).join('')}<th scope="col">Total</th></tr></thead><tbody>${coverageRows}</tbody></table></div>` +
      `<figcaption class="exhibit-note">Counts are findings in this report, grouped by the report's control catalog. An empty row means no finding this period, not an absence of risk.</figcaption></figure>`;
    return `<section class="card briefing-overview"><h2>Findings at a glance</h2><nav class="review-map" aria-label="Review map">${findingsExhibit}${coverageExhibit}</nav></section>`;
  }

  function renderFindingBlocks(part) {
    part = part.replace(/^(<h2>Evidence and Decisions<\/h2>\s*)<p>((?:(?!<\/p>)[\s\S])*)<\/p>/, '$1<p class="section-dek">$2</p>');
    return part.replace(
      /<h3 id="finding-(\d+)" tabindex="-1">([\s\S]*?)<\/h3>((?:\s*<p>[\s\S]*?<\/p>)*)/g,
      (match, number, title, body) => {
        const fields = (body.match(/<p>[\s\S]*?<\/p>/g) || [])
          .map(paragraph => /^<p><strong>([^<]+):<\/strong>\s*([\s\S]*)<\/p>$/.exec(paragraph));
        if (fields.length !== FINDING_FIELDS.length ||
          fields.some((field, index) => !field || field[1] !== FINDING_FIELDS[index])) return match;
        const value = Object.fromEntries(fields.map(field => [field[1], field[2].trim()]));
        const [priority = '', area = '', ownerPart = ''] = value['Review priority'].split(' · ');
        const level = priority.trim().toLowerCase();
        if (!['high', 'medium', 'low'].includes(level) || !ownerPart.startsWith('Owner: ')) return match;
        return `<article class="finding priority-${level}">` +
          `<header class="finding-header"><span class="finding-number">${pad(number)}</span><div class="finding-heading">` +
          `<p class="finding-kicker"><span class="priority-pill">${priority.trim()} priority</span><span class="finding-area">${area.trim()}</span></p>` +
          `<h3 id="finding-${number}" tabindex="-1">${title}</h3></div></header>` +
          `<div class="finding-body"><div class="finding-main"><p class="finding-lead">${value['Why it matters']}</p>` +
          `<figure class="finding-evidence"><figcaption>Source evidence</figcaption><blockquote>${value['Source evidence']}</blockquote></figure></div>` +
          `<aside class="finding-actions" aria-label="Review actions"><dl>` +
          `<dt>Accountable owner</dt><dd>${ownerPart.slice('Owner: '.length)}</dd>` +
          `<dt>Evidence to request</dt><dd>${value['Evidence to request']}</dd>` +
          `<dt>Decision trigger</dt><dd>${value['Decision trigger']}</dd>` +
          `<dt>Reference controls</dt><dd>${value['Reference controls']}</dd>` +
          `</dl></aside></div></article>`;
      },
    );
  }

  function renderReportSections(markdown, reviewMap = []) {
    // Historical source bytes remain unchanged. Make their classification limit
    // visible without claiming a modern evidence check ran at publication.
    markdown = normalizeReportMarkdown(markdown).replace(
      /^## Key Regulatory Developments\s*\n([\s\S]*?)(?=^## |(?![\s\S]))/gm,
      (_match, content) => {
        const rows = content.split('\n').filter(line => /^\|/.test(line.trim()));
        const dataRows = rows.slice(2);
        const allImplied = dataRows.length > 0 && dataRows.every(line => /\b(?:implied|inferred)\b/i.test(line.split('|')[1] || ''));
        const heading = allImplied ? 'Inferred Control and Governance Implications' : 'Regulatory and Control Context';
        const note = allImplied
          ? 'These are inferred mappings, not verified regulatory changes.'
          : 'This retained report predates separate validation of regulatory changes and inferred control mappings. Verify legal claims against the original regulatory publication.';
        return `## ${heading}\n\n${note}\n\n${content}`;
      },
    );
    const html = renderMarkdown(markdown, true);
    // The build supplies a bounded projection from the exact validated plan.
    // A map must have one entry per rendered finding or it is omitted entirely.
    const evidence = html.match(/<h2>Evidence and Decisions<\/h2>([\s\S]*?)(?=<h2>|$)/);
    const findingCount = evidence ? (evidence[1].match(/<h3>/g) || []).length : 0;
    const hasMap = Array.isArray(reviewMap) && reviewMap.length > 0 && reviewMap.length <= 6 &&
      reviewMap.length === findingCount && html.includes('<h2>Executive Summary</h2>') &&
      reviewMap.every(row => row && typeof row.focus === 'string' && row.focus.length > 0 &&
        typeof row.control === 'string' && row.control.length > 0 && ['High', 'Medium', 'Low'].includes(row.priority) &&
        ['undefined', 'string'].includes(typeof row.headline) && ['undefined', 'string'].includes(typeof row.owner));
    const stats = hasMap ? reportStatistics(markdown, reviewMap) : null;
    return html
      .split(/(?=<h2>)/)
      .map(part => part.replace(/^\s*(?:<hr>\s*)+/, '').replace(/(?:\s*<hr>)+\s*$/, '').trim())
      .filter(Boolean)
      .map(part => {
        if (hasMap && part.startsWith('<h2>Evidence and Decisions</h2>')) {
          let index = 0;
          part = part.replace(/<h3>/g, () => `<h3 id="finding-${++index}" tabindex="-1">`);
          return `<section class="card evidence-section">${renderFindingBlocks(part)}</section>`;
        }
        if (hasMap && part.startsWith('<h2>Executive Summary</h2>')) {
          return `<section class="card executive-summary">${renderSummary(part, stats)}</section>${renderOverview(reviewMap, stats)}`;
        }
        return `<section class="card">${part}</section>`;
      })
      .join('');
  }

  function renderReportDocument(markdown, reviewMap = [], origins = {}) {
    const report = parseReportDocument(markdown);
    const html = renderReportSections(report.bodyMarkdown, reviewMap) + renderReportMetadata(report.metadata);
    // Only reader link targets change. Stored markdown, evidence, labels and
    // timestamps remain publication-era records, including their original URLs.
    return html.replace(/href="([^"]*)"/g, (attribute, url) => {
      for (const [origin, emitted] of Object.entries(origins)) {
        if (url.startsWith(origin)) return `href="${escapeAttribute(emitted)}${url.slice(origin.length)}"`;
      }
      return attribute;
    });
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
