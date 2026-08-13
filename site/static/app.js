// Page controller for the GRC report: load the generated Markdown, render it
// through the canonical renderer, wrap sections into cards, and wire the
// reading aids (contents index, navigation, theme, collapse).
(function () {
  const reportEl = document.getElementById('report');
  const generatedEl = document.getElementById('generated');
  const themeBtn = document.getElementById('themeToggle');
  const mobileToc = document.getElementById('mobileToc');

  const renderer = window.GRCInsightRenderer;
  const tagCatalog = window.GRCInsightTags;

  const escapeHtml = renderer.escapeHtml;
  let sidebarObserver = null;
  let topbarObserver = null;

  const ICON_COLLAPSE = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICON_EXPAND = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICON_COPY = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M15 3H6a2 2 0 0 0-2 2v9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="9" y="9" width="12" height="12" rx="2" stroke="currentColor" stroke-width="2"/></svg>';
  const ICON_CHECK = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M5 12.5l4 4L19 6.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  function slugify(text) {
    return text.trim().toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-');
  }

  function sectionHeadingTitle(heading) {
    if (!heading) return '';
    const clone = heading.cloneNode(true);
    clone.querySelectorAll('.anchor-link, .heading-actions').forEach(node => node.remove());
    return clone.textContent.trim();
  }

  function setGeneratedLabel(md) {
    const match = md.match(/\*\*Generated:\*\*\s*(.+)/);
    if (!match || !generatedEl) return;
    const raw = match[1].trim();
    const parsed = new Date(raw);
    const pretty = isNaN(parsed.getTime())
      ? raw
      : parsed.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        timeZone: 'UTC',
      });
    generatedEl.textContent = `Generated ${pretty}`;
    generatedEl.setAttribute('datetime', raw);
  }

  // The canonical renderer creates complete report cards for both the build
  // and the browser. The controller only adds progressive heading controls.
  function enhanceSections(node) {
    Array.from(node.querySelectorAll('.card')).forEach(card => {
      const child = card.querySelector('h2');
      if (!child || child.querySelector('.heading-actions')) return;
      const title = sectionHeadingTitle(child);
      child.id = slugify(title);

      const anchor = document.createElement('a');
      anchor.href = `#${child.id}`;
      anchor.className = 'anchor-link';
      anchor.textContent = '#';
      anchor.setAttribute('aria-label', `Link to ${title}`);
      child.appendChild(anchor);

      const actions = document.createElement('span');
      actions.className = 'heading-actions';

      const copy = document.createElement('button');
      copy.className = 'copy-link';
      copy.type = 'button';
      copy.setAttribute('data-target', child.id);
      copy.setAttribute('aria-label', `Copy link to ${title}`);
      copy.title = 'Copy link';
      copy.innerHTML = ICON_COPY;
      actions.appendChild(copy);

      if (!card.classList.contains('report-provenance')) {
        const toggle = document.createElement('button');
        toggle.className = 'collapse-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'true');
        toggle.setAttribute('aria-label', `Collapse ${title}`);
        toggle.title = 'Collapse section';
        toggle.innerHTML = ICON_COLLAPSE;
        actions.appendChild(toggle);
      }

      child.appendChild(actions);
    });
  }

  // Highlight only terms with authoritative destinations. Anything that looks
  // like a link must behave like one.
  function highlightPills(node) {
    const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT, {
      acceptNode(textNode) {
        const parent = textNode.parentElement;
        if (!parent || parent.closest('a, .pill, code, pre, button')) return NodeFilter.FILTER_REJECT;
        const segments = tagCatalog.tokenizeComplianceTerms(textNode.nodeValue || '');
        return segments.some(segment => segment.pillClass)
          ? NodeFilter.FILTER_ACCEPT
          : NodeFilter.FILTER_REJECT;
      },
    });
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach(textNode => {
      const fragment = document.createDocumentFragment();
      const text = textNode.nodeValue || '';
      tagCatalog.tokenizeComplianceTerms(text).forEach(segment => {
        if (!segment.pillClass) {
          fragment.appendChild(document.createTextNode(segment.text));
          return;
        }

        const safeUrl = segment.url ? renderer.sanitizeMarkdownUrl(segment.url) : null;
        if (!safeUrl) {
          fragment.appendChild(document.createTextNode(segment.text));
          return;
        }
        const pill = document.createElement('a');
        pill.className = `pill ${segment.pillClass} reference-link`;
        pill.textContent = segment.text;
        pill.href = safeUrl;
        pill.target = '_blank';
        pill.rel = 'noopener';
        pill.title = `Open the official ${segment.label} reference`;
        pill.setAttribute(
          'aria-label',
          `${segment.text}: official ${segment.categoryLabel.toLowerCase()} reference`,
        );
        fragment.appendChild(pill);
      });
      textNode.replaceWith(fragment);
    });
  }

  function sectionHeadings() {
    return Array.from(document.querySelectorAll('#report .card h2'));
  }

  function buildSidebar() {
    const toc = document.getElementById('toc');
    if (!toc) return;
    const h2s = sectionHeadings();
    const all = Array.from(document.querySelectorAll('#report .card h2, #report .card h3'));
    const blocks = h2s.map(h2 => {
      const subs = [];
      for (let i = all.indexOf(h2) + 1; i < all.length; i++) {
        if (all[i].tagName === 'H2') break;
        const sub = all[i];
        sub.id = sub.id || slugify(sub.textContent);
        subs.push({ id: sub.id, title: sub.textContent.trim() });
      }
      return { id: h2.id, title: sectionHeadingTitle(h2), subs };
    });

    toc.innerHTML = blocks.map(b => {
      const sub = b.subs.map(s => `<li><a href="#${s.id}">${escapeHtml(s.title)}</a></li>`).join('');
      return `<details><summary><a href="#${b.id}">${escapeHtml(b.title)}</a></summary>${sub ? `<ul>${sub}</ul>` : ''}</details>`;
    }).join('');

    const links = Array.from(toc.querySelectorAll('a'));
    const linkFor = new Map(h2s.map(h => [h.id, links.find(l => l.getAttribute('href') === `#${h.id}`)]));
    if (sidebarObserver) sidebarObserver.disconnect();
    sidebarObserver = new IntersectionObserver(entries => {
      entries.forEach(e => {
        const link = linkFor.get(e.target.id);
        if (link && e.isIntersecting) {
          links.forEach(l => l.classList.remove('active'));
          link.classList.add('active');
        }
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => sidebarObserver.observe(h));

    if (mobileToc) {
      mobileToc.innerHTML = '<option value="">Jump to section</option>' +
        h2s.map(h => `<option value="${h.id}">${escapeHtml(sectionHeadingTitle(h))}</option>`).join('');
      mobileToc.onchange = e => {
        if (e.target.value) document.getElementById(e.target.value)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        e.target.value = '';
      };
    }

    const isMobile = window.matchMedia('(max-width: 900px)').matches;
    const stored = JSON.parse(localStorage.getItem('tocOpen') || '{}');
    Array.from(toc.querySelectorAll('details')).forEach((d, idx) => {
      const id = blocks[idx]?.id || `sec-${idx}`;
      d.open = stored[id] !== undefined ? !!stored[id] : (!isMobile || idx === 0);
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
    const h2s = sectionHeadings();
    bar.innerHTML = h2s.map(h => `<a class="chip" href="#${h.id}"><span class="chip-icon">§</span>${escapeHtml(sectionHeadingTitle(h))}</a>`).join('');
    const chips = Array.from(bar.querySelectorAll('.chip'));
    const chipFor = new Map(h2s.map(h => [h.id, chips.find(c => c.getAttribute('href') === `#${h.id}`)]));
    if (topbarObserver) topbarObserver.disconnect();
    topbarObserver = new IntersectionObserver(entries => {
      entries.forEach(e => {
        const chip = chipFor.get(e.target.id);
        if (chip && e.isIntersecting) {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
        }
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => topbarObserver.observe(h));
  }

  function applyCollapsedState() {
    const map = JSON.parse(localStorage.getItem('cardCollapsed') || '{}');
    const isMobile = window.matchMedia('(max-width: 900px)').matches;
    const collapsibleCards = Array.from(document.querySelectorAll('#report .card'))
      .filter(card => !card.classList.contains('report-provenance'));
    collapsibleCards.forEach((card, idx) => {
      const h2 = card.querySelector('h2');
      if (!h2) return;
      const collapsed = Object.prototype.hasOwnProperty.call(map, h2.id)
        ? !!map[h2.id]
        : (isMobile && idx !== 0);
      setCardCollapsed(card, collapsed, false);
    });
  }

  function setCardCollapsed(card, collapsed, persist) {
    card.classList.toggle('collapsed', collapsed);
    const toggle = card.querySelector('.collapse-toggle');
    if (toggle) {
      toggle.setAttribute('aria-expanded', String(!collapsed));
      toggle.innerHTML = collapsed ? ICON_EXPAND : ICON_COLLAPSE;
      toggle.title = collapsed ? 'Expand section' : 'Collapse section';
      const title = sectionHeadingTitle(card.querySelector('h2'));
      toggle.setAttribute('aria-label', `${collapsed ? 'Expand' : 'Collapse'} ${title}`);
    }
    if (persist) {
      const map = JSON.parse(localStorage.getItem('cardCollapsed') || '{}');
      const h2 = card.querySelector('h2');
      if (h2) { map[h2.id] = collapsed; localStorage.setItem('cardCollapsed', JSON.stringify(map)); }
    }
  }

  function installInteractions() {
    document.addEventListener('click', async e => {
      const toggle = e.target.closest && e.target.closest('.collapse-toggle');
      if (toggle) {
        const card = toggle.closest('.card');
        if (card) setCardCollapsed(card, !card.classList.contains('collapsed'), true);
        return;
      }
      const copy = e.target.closest && e.target.closest('.copy-link');
      if (copy) {
        const url = new URL(window.location.href);
        url.hash = copy.getAttribute('data-target');
        const status = document.getElementById('copyStatus');
        try {
          if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
          await navigator.clipboard.writeText(url.toString());
          copy.classList.add('copied');
          copy.innerHTML = ICON_CHECK;
          copy.title = 'Link copied';
          copy.setAttribute('aria-label', 'Link copied');
          if (status) status.textContent = 'Link copied';
          setTimeout(() => {
            copy.classList.remove('copied');
            copy.innerHTML = ICON_COPY;
            copy.title = 'Copy link';
            const heading = copy.closest('h2');
            copy.setAttribute('aria-label', `Copy link to ${sectionHeadingTitle(heading)}`);
          }, 1500);
        } catch (_) {
          if (status) status.textContent = 'Unable to copy link';
        }
      }
    });

    document.addEventListener('keydown', e => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (e.altKey || e.ctrlKey || e.metaKey || e.target.isContentEditable) return;
      if (['a', 'input', 'textarea', 'select', 'button'].includes(tag)) return;
      const h2s = sectionHeadings();
      if (!h2s.length) return;
      const y = window.scrollY + 100;
      let idx = 0;
      for (let i = 0; i < h2s.length; i++) {
        if (h2s[i].getBoundingClientRect().top + window.scrollY - 90 <= y) idx = i;
      }
      const key = e.key.toLowerCase();
      if (key === 'j') { e.preventDefault(); h2s[Math.min(h2s.length - 1, idx + 1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (key === 'k') { e.preventDefault(); h2s[Math.max(0, idx - 1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (key === 'c') {
        const card = h2s[idx]?.closest('.card');
        if (card?.querySelector('.collapse-toggle')) {
          e.preventDefault();
          setCardCollapsed(card, !card.classList.contains('collapsed'), true);
        }
      }
    });
  }

  function renderReport(md) {
    setGeneratedLabel(md);
    reportEl.innerHTML = renderer.renderReportDocument(md);
    enhanceSections(reportEl);
    applyCollapsedState();
    highlightPills(reportEl);
    buildSidebar();
    buildTopbar();
  }

  const hasPrerenderedReport = reportEl.dataset.prerendered === 'true' && reportEl.querySelector('.card');
  if (hasPrerenderedReport) {
    enhanceSections(reportEl);
    applyCollapsedState();
    highlightPills(reportEl);
    buildSidebar();
    buildTopbar();
  } else {
    reportEl.innerHTML = '<div class="card report-status"><p>Loading report…</p></div>';
  }
  installInteractions();
  fetch('index.md', { cache: 'no-store' })
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text(); })
    .then(renderReport)
    .catch(() => {
      if (!hasPrerenderedReport) {
        reportEl.innerHTML = '<div class="card report-status"><p>Unable to load the report. Please refresh to try again.</p></div>';
      }
    });

  // Theme toggle (persisted; otherwise follows the reader's system theme).
  function applyTheme(mode) {
    document.body.classList.toggle('light', mode === 'light');
    if (themeBtn) {
      const next = mode === 'light' ? 'dark' : 'light';
      themeBtn.setAttribute('aria-label', `Switch to ${next} theme`);
      themeBtn.title = `Switch to ${next} theme`;
    }
  }
  const preferredTheme = window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
  applyTheme(localStorage.getItem('theme') || preferredTheme);
  themeBtn && themeBtn.addEventListener('click', () => {
    const next = document.body.classList.contains('light') ? 'dark' : 'light';
    localStorage.setItem('theme', next);
    applyTheme(next);
  });

  // Back-to-top button and reading-progress bar.
  const back = document.getElementById('backToTop');
  const progress = document.getElementById('progress');
  window.addEventListener('scroll', () => {
    const y = window.scrollY || document.documentElement.scrollTop;
    if (back) back.classList.toggle('show', y > 280);
    const doc = document.documentElement;
    const scrollable = doc.scrollHeight - doc.clientHeight;
    if (progress) progress.style.width = (scrollable > 0 ? Math.min(100, (y / scrollable) * 100) : 0) + '%';
  }, { passive: true });
  back && back.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
})();
