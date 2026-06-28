// Page controller for the GRC report: load the generated Markdown, render it
// through the canonical renderer, wrap sections into cards, and wire the
// reading aids (contents index, navigation, theme, collapse).
(function () {
  const reportEl = document.getElementById('report');
  const generatedEl = document.getElementById('generated');
  const themeBtn = document.getElementById('themeToggle');
  const mobileToc = document.getElementById('mobileToc');

  const renderer = window.GRCInsightRenderer;
  const tagCategories = window.GRCInsightTags.categories;

  const escapeHtml = renderer.escapeHtml;
  let sidebarObserver = null;
  let topbarObserver = null;

  const ICON_COLLAPSE = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  const ICON_EXPAND = '<svg class="icon" width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>';

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
      : parsed.toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' });
    generatedEl.textContent = `Generated ${pretty}`;
  }

  // Wrap everything under each h2 into a card and attach heading actions
  // (anchor link, copy link, collapse). Content before the first h2 is dropped.
  function wrapSections(node) {
    const fragment = document.createDocumentFragment();
    let card = null;
    Array.from(node.childNodes).forEach(child => {
      if (child.nodeType === 1 && child.tagName === 'H2') {
        if (card) fragment.appendChild(card);
        card = document.createElement('div');
        card.className = 'card';
        child.id = slugify(child.textContent);

        const anchor = document.createElement('a');
        anchor.href = `#${child.id}`;
        anchor.className = 'anchor-link';
        anchor.textContent = '#';
        child.appendChild(anchor);

        const actions = document.createElement('span');
        actions.className = 'heading-actions';

        const copy = document.createElement('button');
        copy.className = 'copy-link';
        copy.type = 'button';
        copy.setAttribute('data-target', child.id);
        copy.title = 'Copy link';
        copy.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M15 3H6a2 2 0 0 0-2 2v9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="9" y="9" width="12" height="12" rx="2" stroke="currentColor" stroke-width="2"/></svg>';
        actions.appendChild(copy);

        const toggle = document.createElement('button');
        toggle.className = 'collapse-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'true');
        toggle.title = 'Collapse section';
        toggle.innerHTML = ICON_COLLAPSE;
        actions.appendChild(toggle);

        child.appendChild(actions);
        card.appendChild(child);
      } else if (card) {
        card.appendChild(child);
      }
    });
    if (card) fragment.appendChild(card);
    node.innerHTML = '';
    node.appendChild(fragment);
  }

  // Highlight known compliance terms inline as pills.
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
    Array.from(document.querySelectorAll('#report .card')).forEach((card, idx) => {
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
    }
    if (persist) {
      const map = JSON.parse(localStorage.getItem('cardCollapsed') || '{}');
      const h2 = card.querySelector('h2');
      if (h2) { map[h2.id] = collapsed; localStorage.setItem('cardCollapsed', JSON.stringify(map)); }
    }
  }

  function installInteractions() {
    document.addEventListener('click', e => {
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
        navigator.clipboard && navigator.clipboard.writeText(url.toString());
        const original = copy.title;
        copy.title = 'Copied';
        setTimeout(() => { copy.title = original; }, 800);
      }
    });

    document.addEventListener('keydown', e => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (['input', 'textarea', 'select', 'button'].includes(tag)) return;
      const h2s = sectionHeadings();
      if (!h2s.length) return;
      const y = window.scrollY + 100;
      let idx = 0;
      for (let i = 0; i < h2s.length; i++) {
        if (h2s[i].getBoundingClientRect().top + window.scrollY - 90 <= y) idx = i;
      }
      if (['j', 'ArrowDown'].includes(e.key)) { e.preventDefault(); h2s[Math.min(h2s.length - 1, idx + 1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (['k', 'ArrowUp'].includes(e.key)) { e.preventDefault(); h2s[Math.max(0, idx - 1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (e.key === 'c') { const card = h2s[idx]?.closest('.card'); if (card) setCardCollapsed(card, !card.classList.contains('collapsed'), true); }
    });
  }

  function renderReport(md) {
    setGeneratedLabel(md);
    reportEl.innerHTML = renderer.renderMarkdown(md);
    wrapSections(reportEl);
    applyCollapsedState();
    highlightPills(reportEl);
    buildSidebar();
    buildTopbar();
    installInteractions();
  }

  reportEl.innerHTML = '<div class="card report-status"><p>Loading report…</p></div>';
  fetch('index.md', { cache: 'no-store' })
    .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text(); })
    .then(renderReport)
    .catch(() => {
      reportEl.innerHTML = '<div class="card report-status"><p>Unable to load the report. Please refresh to try again.</p></div>';
    });

  // Theme toggle (persisted; dark is the default).
  function applyTheme(mode) {
    document.body.classList.toggle('light', mode === 'light');
  }
  applyTheme(localStorage.getItem('theme') || 'dark');
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
