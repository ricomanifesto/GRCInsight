// Minimal markdown renderer and enhancer for the report
(function () {
  const el = {
    generated: document.getElementById('generated'),
    report: document.getElementById('report'),
  };
  const themeBtn = document.getElementById('themeToggle');
  const mobileToc = document.getElementById('mobileToc');
  let originalMd = null;
  let sidebarObserver = null;
  let topbarObserver = null;
  let currentSectionObserver = null;

  const tagCategories = window.GRCInsightTags.categories;
  const sectionMetadata = window.GRCInsightMetadata;
  const sectionFilters = window.GRCInsightFilters;
  const archiveDigest = window.GRCInsightArchive;

  function escapeHtml(s) {
    return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
  }

  const renderMarkdownLink = window.GRCInsightRenderer.renderMarkdownLink;
  const sanitizeMarkdownUrl = window.GRCInsightRenderer.sanitizeMarkdownUrl;
  const escapeAttribute = window.GRCInsightRenderer.escapeAttribute;

  function renderArchiveDigest(markdown) {
    const container = document.getElementById('archiveDigest');
    if (!container || !archiveDigest || !archiveDigest.buildReports) return;
    const reports = archiveDigest.buildReports(markdown || '');
    if (!reports.find(report => report.id === archiveDigest.currentReportId)) return;
    const entries = reports.map(report => {
      const isCurrent = report.id === archiveDigest.currentReportId;
      const tags = Array.isArray(report.tags) ? report.tags : [];
      const highlights = Array.isArray(report.highlights) ? report.highlights : [];
      const href = sanitizeMarkdownUrl(report.href || '#') || '#';
      return `
        <article class="archive-entry${isCurrent ? ' current' : ''}">
          <div class="archive-entry-main">
            <div class="archive-entry-kicker">${escapeHtml(report.status || 'Archived')} · ${escapeHtml(report.period || 'Unspecified period')}</div>
            <h3><a href="${escapeAttribute(href)}">${escapeHtml(report.title || 'Untitled report')}</a></h3>
            <p>${escapeHtml(report.summary || 'No digest summary available.')}</p>
            <ul>${highlights.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
          </div>
          <div class="archive-entry-meta">
            <time datetime="${escapeAttribute(report.generatedAt || '')}">${escapeHtml((report.generatedAt || '').slice(0, 10) || 'Unknown date')}</time>
            <div class="archive-tags">${tags.map(tag => `<span>${escapeHtml(tag)}</span>`).join('')}</div>
          </div>
        </article>
      `;
    }).join('');
    container.innerHTML = `
      <div class="archive-card">
        <div>
          <p class="archive-kicker">Digest archive</p>
          <h2>Current report and archive trail</h2>
        </div>
        <p class="archive-summary">The latest generated report remains the default view. This digest trail keeps report metadata, highlights, and review context explicit as snapshots are added.</p>
        <div class="archive-list">${entries}</div>
      </div>
    `;
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
      const content = m[2];
      if (idx === 0) { open(indent); level = indent; }
      else if (indent > level) { open(indent - level); level = indent; }
      else if (indent < level) { close(level - indent); level = indent; }
      html += `<li>${content}</li>`;
    });
    close(level);
    return html;
  }

  function renderTable(block) {
    const rows = block.trim().split('\n').filter(r => r.trim());
    if (rows.length < 2) return block;
    const parseRow = r => r.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
    const headers = parseRow(rows[0]);
    // Skip separator row (row[1] is dashes like |---|---|)
    const isSep = rows[1] && /^\s*\|?[\s\-:|]+\|?\s*$/.test(rows[1]);
    const startIdx = isSep ? 2 : 1;
    let html = '<div class="table-wrap"><table><thead><tr>';
    headers.forEach(h => { html += `<th>${h}</th>`; });
    html += '</tr></thead><tbody>';
    for (let i = startIdx; i < rows.length; i++) {
      const cells = parseRow(rows[i]);
      html += '<tr>';
      cells.forEach(c => { html += `<td>${c}</td>`; });
      html += '</tr>';
    }
    html += '</tbody></table></div>';
    return html;
  }

  function mdToHtml(md) {
    // Try to extract generated timestamp from the first lines
    const genMatch = md.match(/\*\*Generated:\*\*\s*(.+)/);
    if (genMatch) el.generated.textContent = `Generated ${genMatch[1].trim()}`;

    // Pre-process: extract fenced code blocks before HTML-escaping
    const codeBlocks = [];
    md = md.replace(/^```[\s\S]*?^```/gm, m => {
      const code = m.replace(/^```\w*\n?/, '').replace(/\n?```$/, '');
      codeBlocks.push(code);
      return `%%CODEBLOCK_${codeBlocks.length - 1}%%`;
    });

    // Basic markdown transforms: headings, lists, bold
    let html = escapeHtml(md);

    // Restore code blocks as <pre>
    html = html.replace(/%%CODEBLOCK_(\d+)%%/g, (_, i) =>
      `<pre><code>${escapeHtml(codeBlocks[+i])}</code></pre>`);

    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Italic
    html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');
    // Headings (#### before ### before ## before #)
    html = html.replace(/^####\s+(.*)$/gm, '<h4>$1</h4>');
    html = html.replace(/^###\s+(.*)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##\s+(.*)$/gm, '<h2>$1</h2>');
    html = html.replace(/^#\s+(.*)$/gm, '<h1>$1</h1>');
    // Markdown tables: consecutive lines starting with | (must run before HR to avoid eating separator rows)
    html = html.replace(/^(?:\|.+\|(?:\n|$)){2,}/gm, m => renderTable(m));
    // Horizontal rules (--- or ___ or ***)
    html = html.replace(/^-{3,}$/gm, '<hr>');
    html = html.replace(/^_{3,}$/gm, '<hr>');
    html = html.replace(/^\*{3,}$/gm, '<hr>');
    // Blockquotes (> lines)
    html = html.replace(/^(?:&gt;\s?.*(?:\n|$))+/gm, m => {
      const inner = m.replace(/^&gt;\s?/gm, '').trim();
      return `<blockquote>${inner}</blockquote>`;
    });
    // Links: [text](url)
    html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, (_, text, url) => renderMarkdownLink(text, url));
    // Unordered lists (support nested lists via indentation, 2 spaces per level)
    html = html.replace(/^(?:\s*-\s+.*(?:\n|$))+?/gm, m => renderNestedList(m));
    // Ordered lists (consecutive lines starting with digits)
    html = html.replace(/^(?:\d+\.\s+.*(?:\n|$))+/gm, m => {
      const items = m.trim().split(/\n/).filter(l => /^\d+\.\s+/.test(l));
      return '<ol>' + items.map(l => `<li>${l.replace(/^\d+\.\s+/, '')}</li>`).join('') + '</ol>';
    });
    // Simple paragraphs
    html = html
      .split(/\n\n+/)
      .map(block => /<(h\d|ul|ol|li|strong|table|div|hr|pre|blockquote)/.test(block) ? block : `<p>${block.trim()}</p>`)
      .join('\n');
    // Clean up empty paragraphs
    html = html.replace(/<p>\s*<\/p>/g, '');
    return html;
  }

  function wrapSections(node) {
    // Wrap content under each h2 into a card; drop any leading content before first h2
    const fragment = document.createDocumentFragment();
    let card = null;
    let started = false;
    Array.from(node.childNodes).forEach(n => {
      if (n.nodeType === 1 && n.tagName === 'H2') {
        started = true;
        if (card) fragment.appendChild(card);
        card = document.createElement('div');
        card.className = 'card';
        // Add id + anchor link
        const id = n.textContent.trim().toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-');
        n.id = id;
        const a = document.createElement('a');
        a.href = `#${id}`;
        a.className = 'anchor-link';
        a.textContent = '#';
        n.appendChild(a);
        // Wrap action buttons in a container that shows on hover
        const actions = document.createElement('span');
        actions.className = 'heading-actions';
        const copy = document.createElement('button');
        copy.className = 'copy-link';
        copy.type = 'button';
        copy.setAttribute('data-target', id);
        copy.title = 'Copy link';
        copy.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M15 3H6a2 2 0 0 0-2 2v9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="9" y="9" width="12" height="12" rx="2" stroke="currentColor" stroke-width="2"/></svg>';
        actions.appendChild(copy);
        const toggle = document.createElement('button');
        toggle.className = 'collapse-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'true');
        toggle.title = 'Collapse section';
        toggle.innerHTML = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        actions.appendChild(toggle);
        const focus = document.createElement('button');
        focus.className = 'focus-toggle';
        focus.type = 'button';
        focus.title = 'Focus this section';
        focus.innerHTML = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>';
        actions.appendChild(focus);
        n.appendChild(actions);
        card.appendChild(n);
      } else if (started && card) {
        card.appendChild(n);
      }
      // else: drop preface content before first H2
    });
    if (card) fragment.appendChild(card);
    node.innerHTML = '';
    node.appendChild(fragment);
    Array.from(node.querySelectorAll('.card')).forEach(c => {
      const h2 = c.querySelector('h2');
      if (!h2) return;
      const title = (h2.childNodes[0]?.textContent || '').trim();
      const metadata = sectionMetadata.deriveSectionMetadata(title, c.textContent || '');
      h2.insertAdjacentHTML('afterend', sectionMetadata.renderSectionMetadata(metadata));
    });
  }

  function highlightPills(node) {
    const terms = tagCategories
      .flatMap(category => category.terms.map(term => ({ term, pillClass: category.pillClass })))
      .sort((a, b) => b.term.length - a.term.length);
    if (!terms.length) return;

    const escapeRegExp = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`\\b(${terms.map(item => escapeRegExp(item.term)).join('|')})\\b`, 'gi');
    const termMap = new Map(terms.map(item => [item.term.toLowerCase(), item.pillClass]));
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
      acceptNode(textNode) {
        const parent = textNode.parentElement;
        if (!parent || parent.closest('.pill')) return NodeFilter.FILTER_REJECT;
        if (!pattern.test(textNode.nodeValue || '')) return NodeFilter.FILTER_REJECT;
        pattern.lastIndex = 0;
        return NodeFilter.FILTER_ACCEPT;
      },
    });
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach(textNode => {
      const fragment = document.createDocumentFragment();
      const text = textNode.nodeValue || '';
      let cursor = 0;
      text.replace(pattern, (match, _term, offset) => {
        if (offset > cursor) fragment.appendChild(document.createTextNode(text.slice(cursor, offset)));
        const pill = document.createElement('span');
        pill.className = `pill ${termMap.get(match.toLowerCase())}`;
        pill.textContent = match;
        fragment.appendChild(pill);
        cursor = offset + match.length;
        return match;
      });
      if (cursor < text.length) fragment.appendChild(document.createTextNode(text.slice(cursor)));
      textNode.replaceWith(fragment);
    });
  }

  function visibleSectionHeadings() {
    return Array.from(document.querySelectorAll('#report .card:not(.filtered-out) h2'));
  }

  function clearFocusMode() {
    document.body.classList.remove('focus-mode');
    document.querySelectorAll('.card').forEach(card => card.classList.remove('focused'));
    document.querySelectorAll('.focus-toggle').forEach(button => {
      button.textContent = 'Focus';
      button.title = 'Focus this section';
    });
  }

  function collectSection(card) {
    const heading = card.querySelector('h2');
    const metadataEl = card.querySelector('.section-meta');
    const pills = Array.from(card.querySelectorAll('.pill'));
    const pillClasses = tagCategories.map(category => category.pillClass);
    const sectionTagCategories = pills
      .flatMap(pill => pillClasses.filter(name => pill.classList.contains(name)));
    const contentClone = card.cloneNode(true);
    contentClone.querySelectorAll('.section-meta, .heading-actions').forEach(node => node.remove());
    return {
      id: heading ? heading.id : '',
      title: heading ? (heading.childNodes[0]?.textContent || '').trim() : '',
      text: contentClone.textContent || '',
      tagCategories: Array.from(new Set(sectionTagCategories)),
      tagTerms: pills.map(pill => pill.textContent.trim()).filter(Boolean),
      metadata: {
        reviewStatus: metadataEl ? metadataEl.getAttribute('data-review-status') : '',
        obligations: metadataEl ? metadataEl.getAttribute('data-obligations') : '',
        gaps: metadataEl ? metadataEl.getAttribute('data-gaps') : '',
        deadlines: metadataEl ? metadataEl.getAttribute('data-deadlines') : '',
        owners: metadataEl ? metadataEl.getAttribute('data-owners') : '',
        evidence: metadataEl ? metadataEl.getAttribute('data-evidence') : '',
      },
      element: card,
    };
  }

  function installSectionFilters() {
    const search = document.getElementById('sectionSearch');
    const status = document.getElementById('statusFilter');
    const tag = document.getElementById('tagFilter');
    const owner = document.getElementById('ownerFilter');
    const evidence = document.getElementById('evidenceFilter');
    const clear = document.getElementById('clearFilters');
    const summary = document.getElementById('filterSummary');
    const activeChips = document.getElementById('activeFilterChips');
    const empty = document.getElementById('emptyResults');
    const quickFilters = document.getElementById('statusQuickFilters');
    if (!search || !status || !tag || !owner || !evidence || !summary || !empty || !sectionFilters) return;

    const sections = Array.from(document.querySelectorAll('#report .card')).map(collectSection);
    const total = sections.length;
    const initialFilters = sectionFilters.parseFilterParams ? sectionFilters.parseFilterParams(window.location.search) : {};
    search.value = initialFilters.query || '';
    status.value = initialFilters.reviewStatus || 'all';
    tag.value = initialFilters.tagCategory || 'all';
    owner.value = initialFilters.ownerCue || 'all';
    evidence.value = initialFilters.evidenceState || 'all';

    function currentFilters() {
      return {
        query: search.value,
        reviewStatus: status.value,
        tagCategory: tag.value,
        ownerCue: owner.value,
        evidenceState: evidence.value,
      };
    }

    function syncFilterParams(filters) {
      if (!sectionFilters.buildFilterParams || !window.history || !window.history.replaceState) return;
      const nextSearch = sectionFilters.buildFilterParams(filters);
      const nextUrl = `${window.location.pathname}${nextSearch}${window.location.hash}`;
      window.history.replaceState(null, '', nextUrl);
    }

    function applyFilters() {
      const filters = currentFilters();
      const matches = new Set(sectionFilters.filterSections(sections, filters));
      sections.forEach(section => {
        const visible = matches.has(section);
        section.element.classList.toggle('filtered-out', !visible);
        section.element.setAttribute('aria-hidden', String(!visible));
      });
      const focusedCard = document.querySelector('.card.focused');
      if (focusedCard && focusedCard.classList.contains('filtered-out')) {
        clearFocusMode();
      }
      const count = matches.size;
      summary.textContent = sectionFilters.summarizeFilterResults
        ? sectionFilters.summarizeFilterResults(count, total, filters)
        : (count === total ? `Showing all ${total} sections` : `Showing ${count} of ${total} sections`);
      renderActiveFilterChips(filters);
      empty.hidden = count !== 0;
      empty.textContent = count === 0
        ? `${summary.textContent}. Clear filters to return to the full report.`
        : 'No matching sections. Clear filters to return to the full report.';
      clear.disabled = count === total && !search.value && status.value === 'all' && tag.value === 'all' && owner.value === 'all' && evidence.value === 'all';
      updateStatusQuickFilters(sections);
      updateNavigationContext(count, total);
      buildSidebar();
      buildTopbar();
      updateCurrentSection();
      syncFilterParams(filters);
    }

    function updateStatusQuickFilters(sections) {
      if (!quickFilters) return;
      const statuses = [
        ['Action required', 'Action'],
        ['Review ready', 'Ready'],
        ['Needs review', 'Needs review'],
      ];
      quickFilters.innerHTML = statuses.map(([value, label]) => {
        const count = sections.filter(section => section.metadata && section.metadata.reviewStatus === value).length;
        const selected = status.value === value;
        return `<button class="status-quick-filter${selected ? ' active' : ''}" type="button" data-status-filter="${value}" aria-label="${label}: ${count} sections" aria-pressed="${selected}" ${count === 0 ? 'disabled' : ''}><span>${label}</span><strong>${count}</strong></button>`;
      }).join('');
    }

    function renderActiveFilterChips(filters) {
      if (!activeChips || !sectionFilters.activeFilterEntries) return;
      const entries = sectionFilters.activeFilterEntries(filters);
      activeChips.hidden = entries.length === 0;
      activeChips.replaceChildren(...entries.map(entry => {
        const button = document.createElement('button');
        button.className = 'active-filter-chip';
        button.type = 'button';
        button.dataset.clearFilter = entry.key;
        button.setAttribute('aria-label', `Clear ${entry.label}`);
        const label = document.createElement('span');
        label.textContent = entry.label;
        const clearMark = document.createElement('span');
        clearMark.className = 'active-filter-chip-clear';
        clearMark.setAttribute('aria-hidden', 'true');
        clearMark.textContent = 'x';
        button.append(label, clearMark);
        return button;
      }));
    }

    [search, status, tag, owner, evidence].forEach(control => {
      control.addEventListener('input', applyFilters);
      control.addEventListener('change', applyFilters);
    });
    function resetFilters() {
      search.value = '';
      status.value = 'all';
      tag.value = 'all';
      owner.value = 'all';
      evidence.value = 'all';
      applyFilters();
      search.focus();
    }

    function clearSingleFilter(filterKey) {
      if (filterKey === 'query') search.value = '';
      if (filterKey === 'reviewStatus') status.value = 'all';
      if (filterKey === 'tagCategory') tag.value = 'all';
      if (filterKey === 'ownerCue') owner.value = 'all';
      if (filterKey === 'evidenceState') evidence.value = 'all';
      applyFilters();
    }

    document.addEventListener('click', event => {
      if (event.target.closest && event.target.closest('#clearFilters')) resetFilters();
      const clearButton = event.target.closest && event.target.closest('[data-clear-filter]');
      if (clearButton) {
        clearSingleFilter(clearButton.dataset.clearFilter);
        return;
      }
      const button = event.target.closest && event.target.closest('[data-status-filter]');
      if (button) {
        const targetStatus = button.dataset.statusFilter || 'all';
        if (status.value === targetStatus) {
          status.value = 'all';
        } else {
          status.value = targetStatus;
        }
        applyFilters();
      }
    });
    clear.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        resetFilters();
      }
    });
    applyFilters();
  }

  function updateNavigationContext(count, total) {
    const text = count === total
      ? `All ${total} sections`
      : (count === 0 ? 'No sections in filtered view' : `${count} filtered sections`);
    ['sidebarFilterState', 'topbarFilterState'].forEach(id => {
      const node = document.getElementById(id);
      if (!node) return;
      node.textContent = text;
      node.dataset.filterState = count === total ? 'all' : (count === 0 ? 'empty' : 'filtered');
    });
  }

  function installAuditSummary() {
    const container = document.getElementById('auditSummary');
    if (!container || !sectionMetadata || !sectionMetadata.summarizeSections) return;
    const sections = Array.from(document.querySelectorAll('#report .card')).map(card => {
      const heading = card.querySelector('h2');
      const metadataEl = card.querySelector('.section-meta');
      return {
        title: heading ? (heading.childNodes[0]?.textContent || '').trim() : 'Untitled section',
        metadata: {
          reviewStatus: metadataEl ? metadataEl.getAttribute('data-review-status') : 'Needs review',
          obligations: metadataEl ? metadataEl.getAttribute('data-obligations') : 'Not detected',
          gaps: metadataEl ? metadataEl.getAttribute('data-gaps') : 'Not detected',
          deadlines: metadataEl ? metadataEl.getAttribute('data-deadlines') : 'Not detected',
          owners: metadataEl ? metadataEl.getAttribute('data-owners') : 'Not detected',
          evidence: metadataEl ? metadataEl.getAttribute('data-evidence') : 'Needs source trail',
        },
      };
    });
    container.innerHTML = sectionMetadata.renderAuditSummary(sectionMetadata.summarizeSections(sections));
  }


  function buildSidebar() {
    const toc = document.getElementById('toc');
    if (!toc) return;
    const h2s = visibleSectionHeadings();
    const all = Array.from(document.querySelectorAll('#report .card:not(.filtered-out) h2, #report .card:not(.filtered-out) h3'));
    // Build nested outline: for each H2, collect following H3s until next H2
    const blocks = h2s.map(h2 => {
      const id = h2.id;
      const title = h2.childNodes[0].textContent.trim();
      const h3s = [];
      for (let i = all.indexOf(h2) + 1; i < all.length; i++) {
        const el = all[i];
        if (el.tagName === 'H2') break;
        if (el.tagName === 'H3') {
          const hid = el.id || el.textContent.trim().toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-');
          el.id = hid;
          h3s.push({ id: hid, title: el.textContent.trim() });
        }
      }
      return { id, title, h3s };
    });

    toc.innerHTML = blocks.map(b => {
      const sub = b.h3s.map(s => `<li><a href="#${s.id}">${s.title}</a></li>`).join('');
      return `<details><summary><a href="#${b.id}">${b.title}</a></summary>${sub ? `<ul>${sub}</ul>` : ''}</details>`;
    }).join('') || '<p class="nav-empty">No sections in filtered view</p>';

    // Highlight on scroll
    const links = Array.from(toc.querySelectorAll('a'));
    const map = new Map(h2s.map((h, i) => [h.id, links.find(l => l.getAttribute('href') === `#${h.id}`)]));
    if (sidebarObserver) sidebarObserver.disconnect();
    sidebarObserver = new IntersectionObserver(entries => {
      entries.forEach(e => {
        const link = map.get(e.target.id);
        if (!link) return;
        if (e.isIntersecting) {
          links.forEach(l => l.classList.remove('active'));
          link.classList.add('active');
        }
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => sidebarObserver.observe(h));

    // Mobile TOC
    if (mobileToc) {
      mobileToc.innerHTML = '<option value="">Jump to section</option>' +
        (h2s.length
          ? h2s.map(h => `<option value="${h.id}">${h.childNodes[0].textContent.trim()}</option>`).join('')
          : '<option value="" disabled>No sections in filtered view</option>');
      mobileToc.onchange = e => {
        const v = e.target.value;
        if (v) document.getElementById(v)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        e.target.value = '';
      };
    }

    // Restore open state from storage. Default: desktop open, mobile collapsed
    const isMobile = window.matchMedia('(max-width: 900px)').matches;
    const stored = JSON.parse(localStorage.getItem('tocOpen') || '{}');
    Array.from(toc.querySelectorAll('details')).forEach((d, idx) => {
      const id = blocks[idx]?.id || `sec-${idx}`;
      if (stored[id] !== undefined) {
        d.open = !!stored[id];
      } else {
        d.open = !isMobile || idx === 0;
      }
      d.addEventListener('toggle', () => {
        const map = JSON.parse(localStorage.getItem('tocOpen') || '{}');
        map[id] = d.open;
        localStorage.setItem('tocOpen', JSON.stringify(map));
      });
    });
  }

  function buildTopbar() {
    const bar = document.getElementById('topbarLinks');
    if (!bar) return;
    const h2s = visibleSectionHeadings();
    bar.innerHTML = h2s.length
      ? h2s.map(h => `<a class="chip" href="#${h.id}"><span class="chip-icon">§</span>${h.childNodes[0].textContent.trim()}</a>`).join('')
      : '<span class="nav-empty">No sections in filtered view</span>';
    const chips = Array.from(bar.querySelectorAll('.chip'));
    const map = new Map(h2s.map(h => [h.id, chips.find(c => c.getAttribute('href') === `#${h.id}`)]));
    if (topbarObserver) topbarObserver.disconnect();
    topbarObserver = new IntersectionObserver(entries => {
      entries.forEach(e => {
        const chip = map.get(e.target.id);
        if (!chip) return;
        if (e.isIntersecting) {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
        }
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => topbarObserver.observe(h));
  }

  function applyCollapsedState() {
    const map = JSON.parse(localStorage.getItem('cardCollapsed') || '{}');
    const cards = Array.from(document.querySelectorAll('.card'));
    const isMobile = window.matchMedia('(max-width: 900px)').matches;
    cards.forEach((c, idx) => {
      const h2 = c.querySelector('h2'); if (!h2) return;
      const id = h2.id;
      const title = (h2.childNodes[0]?.textContent || '').trim().toLowerCase();
      const isExec = /executive\s+summary/.test(title);
      const hasSaved = Object.prototype.hasOwnProperty.call(map, id);
      let collapsed;
      if (hasSaved) collapsed = !!map[id];
      else collapsed = isMobile ? idx !== 0 : false;
      if (isExec && !hasSaved) collapsed = false; // default expand Executive Summary
      c.classList.toggle('collapsed', !!collapsed);
      const btn = h2.querySelector('.collapse-toggle');
      if (btn) {
        btn.setAttribute('aria-expanded', String(!collapsed));
        btn.innerHTML = collapsed
          ? '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
          : '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        btn.title = collapsed ? 'Expand section' : 'Collapse section';
      }
    });
  }

  function updateCurrentSection() {
    const lbl = document.getElementById('currentSection');
    if (!lbl) return;
    const h2s = visibleSectionHeadings();
    if (currentSectionObserver) currentSectionObserver.disconnect();
    currentSectionObserver = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const title = e.target.childNodes[0].textContent.trim();
          lbl.textContent = `Current section: ${title}`;
        }
      });
    }, { rootMargin: '-10% 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => currentSectionObserver.observe(h));
  }

  function installNavFabs() {
    const left = document.createElement('button');
    left.id = 'navPrev'; left.className = 'nav-fab left'; left.setAttribute('aria-label', 'Previous section');
    left.innerHTML = '\u2190';
    const right = document.createElement('button');
    right.id = 'navNext'; right.className = 'nav-fab right'; right.setAttribute('aria-label', 'Next section');
    right.innerHTML = '\u2192';
    document.body.appendChild(left); document.body.appendChild(right);
    const getH2s = visibleSectionHeadings;
    function currentIndex() {
      const h2s = getH2s();
      const y = window.scrollY + 100;
      let idx = 0;
      for (let i = 0; i < h2s.length; i++) { if (h2s[i].getBoundingClientRect().top + window.scrollY - 90 <= y) idx = i; }
      return idx;
    }
    left.addEventListener('click', () => {
      const h2s = getH2s(); const idx = Math.max(0, currentIndex() - 1); h2s[idx]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    right.addEventListener('click', () => {
      const h2s = getH2s(); const idx = Math.min(getH2s().length - 1, currentIndex() + 1); h2s[idx]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  function installFocusAndShortcuts() {
    // Focus mode toggle buttons are created in wrapSections
    document.addEventListener('click', e => {
      const t = e.target.closest && e.target.closest('.focus-toggle');
      if (!t) return;
      const card = t.closest('.card');
      if (!card) return;
      const isActive = document.body.classList.toggle('focus-mode');
      document.querySelectorAll('.card').forEach(c => c.classList.remove('focused'));
      if (isActive) card.classList.add('focused');
      // Update all buttons text
      document.querySelectorAll('.focus-toggle').forEach(b => b.textContent = 'Focus');
      t.textContent = isActive ? 'Unfocus' : 'Focus';
    });

    // Collapse/expand individual card + persist state
    document.addEventListener('click', e => {
      const t = e.target.closest && e.target.closest('.collapse-toggle');
      if (!t) return;
      const card = t.closest('.card');
      const h2 = card && card.querySelector('h2');
      if (!card || !h2) return;
      const collapsed = card.classList.toggle('collapsed');
      t.setAttribute('aria-expanded', String(!collapsed));
      t.innerHTML = collapsed
        ? '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
        : '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
      t.title = collapsed ? 'Expand section' : 'Collapse section';
      const map = JSON.parse(localStorage.getItem('cardCollapsed') || '{}');
      map[h2.id] = collapsed;
      localStorage.setItem('cardCollapsed', JSON.stringify(map));
    });

    // Expand/Collapse all
    const expandAll = document.getElementById('expandAll');
    const collapseAll = document.getElementById('collapseAll');
    expandAll && expandAll.addEventListener('click', () => {
      const map = {};
      document.querySelectorAll('.card').forEach(c => c.classList.remove('collapsed'));
      document.querySelectorAll('.collapse-toggle').forEach(b => { b.innerHTML = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'; b.setAttribute('aria-expanded', 'true'); b.title = 'Collapse section'; });
      localStorage.setItem('cardCollapsed', JSON.stringify(map));
    });
    collapseAll && collapseAll.addEventListener('click', () => {
      const map = {};
      document.querySelectorAll('.card').forEach(c => {
        c.classList.add('collapsed');
        const h2 = c.querySelector('h2'); if (h2) map[h2.id] = true;
      });
      document.querySelectorAll('.collapse-toggle').forEach(b => { b.innerHTML = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>'; b.setAttribute('aria-expanded', 'false'); b.title = 'Expand section'; });
      localStorage.setItem('cardCollapsed', JSON.stringify(map));
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select' || tag === 'button') return;
      const h2s = visibleSectionHeadings();
      if (!h2s.length) return;
      const y = window.scrollY + 100; let idx = 0;
      for (let i = 0; i < h2s.length; i++) { if (h2s[i].getBoundingClientRect().top + window.scrollY - 90 <= y) idx = i; }
      if (['j','ArrowDown'].includes(e.key)) { e.preventDefault(); h2s[Math.min(h2s.length-1, idx+1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (['k','ArrowUp'].includes(e.key)) { e.preventDefault(); h2s[Math.max(0, idx-1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (e.key === 'f') { e.preventDefault(); const btn = h2s[idx]?.querySelector('.focus-toggle'); btn && btn.click(); }
      if (e.key === 'Escape') { clearFocusMode(); }
      if (e.key === 'c') { const btn = h2s[idx]?.querySelector('.collapse-toggle'); btn && btn.click(); }
    });
  }


  fetch('index.md', { cache: 'no-store' })
    .then(r => r.text())
    .then(md => {
      originalMd = md;
      renderArchiveDigest(md);
      const html = mdToHtml(md);
      el.report.innerHTML = html;
      wrapSections(el.report);
      // Mark and handle temporary outline placeholder if present
      (function handleTempOutline() {
        const h2s = Array.from(document.querySelectorAll('#report h2'));
        const temp = h2s.find(h => /temporary\s+outline/i.test(h.textContent));
        if (!temp) return;
        const card = temp.parentElement;
        if (!card || !card.classList.contains('card')) return;
        card.classList.add('temp-outline');
        // Add a small note under the heading
        const note = document.createElement('p');
        note.className = 'temp-note';
        note.textContent = 'Temporary placeholder — the full report content will replace this automatically on the next successful run.';
        card.insertBefore(note, temp.nextSibling);
        // If other sections exist, remove the placeholder entirely
        const cards = Array.from(document.querySelectorAll('#report .card'));
        if (cards.length > 1) {
          card.remove();
        }
      })();
      installAuditSummary();
      applyCollapsedState();
      highlightPills(el.report);
      installSectionFilters();
      buildSidebar();
      buildTopbar();
      updateCurrentSection();
      installNavFabs();
      installFocusAndShortcuts();
    })
    .catch(() => {
      el.report.innerHTML = '<div class="card"><p>Unable to load report.</p></div>';
    });

  // Theme toggle
  function applyTheme(mode) {
    if (mode === 'light') document.body.classList.add('light');
    else document.body.classList.remove('light');
  }
  const saved = localStorage.getItem('theme') || 'dark';
  applyTheme(saved);
  themeBtn && themeBtn.addEventListener('click', () => {
    const next = document.body.classList.contains('light') ? 'dark' : 'light';
    localStorage.setItem('theme', next);
    applyTheme(next);
  });

  // Back to top
  const back = document.getElementById('backToTop');
  const onScroll = () => {
    const y = window.scrollY || document.documentElement.scrollTop;
    if (y > 280) back?.classList.add('show'); else back?.classList.remove('show');
    // Progress bar
    const doc = document.documentElement;
    const h = doc.scrollHeight - doc.clientHeight;
    const p = h > 0 ? Math.min(100, (y / h) * 100) : 0;
    const bar = document.getElementById('progress');
    if (bar) bar.style.width = p + '%';
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  back && back.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  // Copy link buttons
  document.addEventListener('click', e => {
    const btn = e.target.closest && e.target.closest('.copy-link');
    if (!btn) return;
    const id = btn.getAttribute('data-target');
    const url = new URL(window.location.href);
    url.hash = id;
    navigator.clipboard && navigator.clipboard.writeText(url.toString());
    btn.textContent = 'Copied';
    setTimeout(() => { btn.textContent = 'Copy'; }, 800);
  });

  // Collapse per-section handled earlier with persistence and icons

  // Expand/Collapse all handled in installFocusAndShortcuts (with persistence)
})();
