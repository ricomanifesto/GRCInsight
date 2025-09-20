// Minimal markdown renderer and enhancer for the report
(function () {
  const el = {
    generated: document.getElementById('generated'),
    report: document.getElementById('report'),
  };
  const themeBtn = document.getElementById('themeToggle');
  const mobileToc = document.getElementById('mobileToc');
  let originalMd = null;

  // Keyword highlighting catalog
  const frameworks = ['ISO 27001', 'ISO/IEC 27001', 'NIST', 'NIST CSF', 'COBIT', 'COSO', 'PCI-DSS'];
  const regulations = ['GDPR', 'CCPA', 'SOX', 'HIPAA', 'FFIEC'];
  const risks = ['Ransomware', 'Extortion', 'Third-party', 'Identity', 'Cloud misconfiguration', 'BEC'];

  function escapeHtml(s) {
    return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
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

  function mdToHtml(md) {
    // Try to extract generated timestamp from the first lines
    const genMatch = md.match(/\*\*Generated:\*\*\s*(.+)/);
    if (genMatch) el.generated.textContent = `Generated ${genMatch[1].trim()}`;

    // Basic markdown transforms: headings, lists, bold
    let html = escapeHtml(md);
    // Bold
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Headings
    html = html.replace(/^###\s+(.*)$/gm, '<h3>$1</h3>');
    html = html.replace(/^##\s+(.*)$/gm, '<h2>$1</h2>');
    html = html.replace(/^#\s+(.*)$/gm, '<h1>$1</h1>');
    // Numbered section headings like "1) Executive Summary" or "2. Section"
    html = html.replace(/^\s*(\d+)[\.)]\s+(.*)$/gm, '<h2>$1) $2</h2>');
    // Lists (support nested lists via indentation, 2 spaces per level)
    html = html.replace(/^(?:\s*-\s+.*(?:\n|$))+?/gm, m => renderNestedList(m));
    // Simple paragraphs
    html = html
      .split(/\n\n+/)
      .map(block => /<(h\d|ul|li|strong)/.test(block) ? block : `<p>${block.trim()}</p>`)
      .join('\n');
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
        const copy = document.createElement('button');
        copy.className = 'copy-link';
        copy.type = 'button';
        copy.setAttribute('data-target', id);
        copy.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M15 3H6a2 2 0 0 0-2 2v9" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><rect x="9" y="9" width="12" height="12" rx="2" stroke="currentColor" stroke-width="2"/></svg><span>Copy</span>';
        n.appendChild(copy);
        const toggle = document.createElement('button');
        toggle.className = 'collapse-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'true');
        toggle.innerHTML = '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Collapse</span>';
        n.appendChild(toggle);
        const focus = document.createElement('button');
        focus.className = 'focus-toggle';
        focus.type = 'button';
        focus.innerHTML = '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><circle cx="12" cy="12" r="3" stroke="currentColor" stroke-width="2"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span>Focus</span>';
        n.appendChild(focus);
        card.appendChild(n);
      } else if (started && card) {
        card.appendChild(n);
      }
      // else: drop preface content before first H2
    });
    if (card) fragment.appendChild(card);
    node.innerHTML = '';
    node.appendChild(fragment);
  }

  function highlightPills(node) {
    let html = node.innerHTML;
    function pillify(list, cls) {
      list.forEach(k => {
        const re = new RegExp(`(\\b${k.replace(/[-/]/g, m=>`\\${m}`)}\\b)`, 'g');
        html = html.replace(re, `<span class="pill ${cls}">$1</span>`);
      });
    }
    pillify(frameworks, 'framework');
    pillify(regulations, 'regulation');
    pillify(risks, 'risk');
    node.innerHTML = html;
  }

  function addSummaryStats(node, sourceText) {
    // Look for Total/GRC counts in provided text (prefer original MD), tolerate separators/newlines
    const haystack = (sourceText || node.textContent || '');
    const m = haystack.match(/Total\s+Articles\s+Analyzed:\s*(\d+)[\s\S]*?GRC[-\s]?Relevant\s+Articles:\s*(\d+)/i);
    if (!m) return;
    const total = m[1], grc = m[2];
    const statGrid = document.createElement('div');
    statGrid.className = 'summary-grid';
    statGrid.innerHTML = `
      <div class="stat"><div class="label">Total Articles</div><div class="value animate" data-target="${total}">0</div></div>
      <div class="stat"><div class="label">GRC‑Relevant</div><div class="value animate" data-target="${grc}">0</div></div>
    `;
    node.insertBefore(statGrid, node.firstChild);
    animateCounters(statGrid.querySelectorAll('.value.animate'));
  }

  function animateCounters(nodes) {
    nodes.forEach(n => {
      const target = parseInt(n.getAttribute('data-target') || '0', 10);
      const start = 0;
      const duration = 800;
      const t0 = performance.now();
      function step(ts) {
        const p = Math.min(1, (ts - t0) / duration);
        const val = Math.floor(start + (target - start) * p);
        n.textContent = String(val);
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
    });
  }

  function buildSidebar() {
    const toc = document.getElementById('toc');
    if (!toc) return;
    const h2s = Array.from(document.querySelectorAll('#report h2'));
    const all = Array.from(document.querySelectorAll('#report h2, #report h3'));
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
    }).join('');

    // Highlight on scroll
    const links = Array.from(toc.querySelectorAll('a'));
    const map = new Map(h2s.map((h, i) => [h.id, links.find(l => l.getAttribute('href') === `#${h.id}`)]));
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        const link = map.get(e.target.id);
        if (!link) return;
        if (e.isIntersecting) {
          links.forEach(l => l.classList.remove('active'));
          link.classList.add('active');
        }
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => obs.observe(h));

    // Mobile TOC
    if (mobileToc) {
      mobileToc.innerHTML = '<option value="">Jump to section</option>' +
        h2s.map(h => `<option value="#${h.id}">${h.childNodes[0].textContent.trim()}</option>`).join('');
      mobileToc.addEventListener('change', e => {
        const v = e.target.value;
        if (v) document.querySelector(v)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        e.target.value = '';
      });
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
    const h2s = Array.from(document.querySelectorAll('#report h2'));
    bar.innerHTML = h2s.map(h => `<a class="chip" href="#${h.id}"><span class="chip-icon">§</span>${h.childNodes[0].textContent.trim()}</a>`).join('');
    const chips = Array.from(bar.querySelectorAll('.chip'));
    const map = new Map(h2s.map(h => [h.id, chips.find(c => c.getAttribute('href') === `#${h.id}`)]));
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        const chip = map.get(e.target.id);
        if (!chip) return;
        if (e.isIntersecting) {
          chips.forEach(c => c.classList.remove('active'));
          chip.classList.add('active');
        }
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => obs.observe(h));
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
          ? '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Expand</span>'
          : '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Collapse</span>';
      }
    });
  }

  function updateCurrentSection() {
    const lbl = document.getElementById('currentSection');
    if (!lbl) return;
    const h2s = Array.from(document.querySelectorAll('#report h2'));
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          const title = e.target.childNodes[0].textContent.trim();
          lbl.textContent = `Current section: ${title}`;
        }
      });
    }, { rootMargin: '-10% 0px -70% 0px', threshold: 0.1 });
    h2s.forEach(h => obs.observe(h));
  }

  function installNavFabs() {
    const left = document.createElement('button');
    left.id = 'navPrev'; left.className = 'nav-fab left'; left.setAttribute('aria-label', 'Previous section');
    left.innerHTML = '\u2190';
    const right = document.createElement('button');
    right.id = 'navNext'; right.className = 'nav-fab right'; right.setAttribute('aria-label', 'Next section');
    right.innerHTML = '\u2192';
    document.body.appendChild(left); document.body.appendChild(right);
    const getH2s = () => Array.from(document.querySelectorAll('#report h2'));
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
        ? '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Expand</span>'
        : '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Collapse</span>';
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
      document.querySelectorAll('.collapse-toggle').forEach(b => { b.innerHTML = '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 10l5-5 5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Collapse</span>'; b.setAttribute('aria-expanded', 'true'); });
      localStorage.setItem('cardCollapsed', JSON.stringify(map));
    });
    collapseAll && collapseAll.addEventListener('click', () => {
      const map = {};
      document.querySelectorAll('.card').forEach(c => {
        c.classList.add('collapsed');
        const h2 = c.querySelector('h2'); if (h2) map[h2.id] = true;
      });
      document.querySelectorAll('.collapse-toggle').forEach(b => { b.innerHTML = '<svg class="icon" width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true"><path d="M7 14l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Expand</span>'; b.setAttribute('aria-expanded', 'false'); });
      localStorage.setItem('cardCollapsed', JSON.stringify(map));
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', e => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea') return;
      const h2s = Array.from(document.querySelectorAll('#report h2'));
      const y = window.scrollY + 100; let idx = 0;
      for (let i = 0; i < h2s.length; i++) { if (h2s[i].getBoundingClientRect().top + window.scrollY - 90 <= y) idx = i; }
      if (['j','ArrowDown'].includes(e.key)) { e.preventDefault(); h2s[Math.min(h2s.length-1, idx+1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (['k','ArrowUp'].includes(e.key)) { e.preventDefault(); h2s[Math.max(0, idx-1)]?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      if (e.key === 'f') { e.preventDefault(); const btn = h2s[idx]?.querySelector('.focus-toggle'); btn && btn.click(); }
      if (e.key === 'Escape') { document.body.classList.remove('focus-mode'); document.querySelectorAll('.card').forEach(c => c.classList.remove('focused')); }
      if (e.key === 'c') { const btn = h2s[idx]?.querySelector('.collapse-toggle'); btn && btn.click(); }
    });
  }


  fetch('index.md', { cache: 'no-store' })
    .then(r => r.text())
    .then(md => {
      originalMd = md;
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
      applyCollapsedState();
      addSummaryStats(el.report, originalMd);
      highlightPills(el.report);
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
