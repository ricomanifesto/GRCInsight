// Minimal markdown renderer and enhancer for the report
(function () {
  const el = {
    generated: document.getElementById('generated'),
    report: document.getElementById('report'),
  };
  const themeBtn = document.getElementById('themeToggle');
  const mobileToc = document.getElementById('mobileToc');
  const searchBox = document.getElementById('searchBox');

  // Keyword highlighting catalog
  const frameworks = ['ISO 27001', 'ISO/IEC 27001', 'NIST', 'NIST CSF', 'COBIT', 'COSO', 'PCI-DSS'];
  const regulations = ['GDPR', 'CCPA', 'SOX', 'HIPAA', 'FFIEC'];
  const risks = ['Ransomware', 'Extortion', 'Third-party', 'Identity', 'Cloud misconfiguration', 'BEC'];

  function escapeHtml(s) {
    return s.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
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
    // Lists
    html = html.replace(/^(?:-\s+.*(?:\n|$))+?/gm, m => {
      const items = m.trim().split(/\n/).map(line => line.replace(/^-\s+/, ''));
      return '<ul>' + items.map(it => `<li>${it}</li>`).join('') + '</ul>';
    });
    // Simple paragraphs
    html = html
      .split(/\n\n+/)
      .map(block => /<(h\d|ul|li|strong)/.test(block) ? block : `<p>${block.trim()}</p>`)
      .join('\n');
    return html;
  }

  function wrapSections(node) {
    // Wrap content under each h2 into a card
    const fragment = document.createDocumentFragment();
    let card = document.createElement('div');
    card.className = 'card';
    Array.from(node.childNodes).forEach(n => {
      if (n.nodeType === 1 && n.tagName === 'H2') {
        fragment.appendChild(card);
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
        card.appendChild(n);
      } else {
        card.appendChild(n);
      }
    });
    fragment.appendChild(card);
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

  function addSummaryStats(node) {
    // Look for "Total Articles Analyzed" line to render stats cards
    const m = node.textContent.match(/Total Articles Analyzed:\s*(\d+)\s*\|\s*GRC-Relevant Articles:\s*(\d+)/i);
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
    bar.innerHTML = h2s.map(h => `<a class="chip" href="#${h.id}">${h.childNodes[0].textContent.trim()}</a>`).join('');
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

  // Search with highlight
  function clearMarks(root) {
    const marks = root.querySelectorAll('mark');
    marks.forEach(m => {
      const t = document.createTextNode(m.textContent || '');
      m.parentNode.replaceChild(t, m);
    });
  }

  function highlightQuery(root, q) {
    if (!q || q.length < 2) { clearMarks(root); return; }
    clearMarks(root);
    const regex = new RegExp(q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode(node) {
        if (!node.nodeValue || !node.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        if (node.parentElement && ['SCRIPT','STYLE','MARK'].includes(node.parentElement.tagName)) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const textNodes = [];
    while (walker.nextNode()) textNodes.push(walker.currentNode);
    textNodes.forEach(node => {
      const text = node.nodeValue;
      if (!regex.test(text)) return;
      const frag = document.createDocumentFragment();
      let lastIndex = 0; regex.lastIndex = 0;
      let m;
      while ((m = regex.exec(text)) !== null) {
        const before = text.slice(lastIndex, m.index);
        if (before) frag.appendChild(document.createTextNode(before));
        const mark = document.createElement('mark');
        mark.textContent = m[0];
        frag.appendChild(mark);
        lastIndex = m.index + m[0].length;
      }
      const after = text.slice(lastIndex);
      if (after) frag.appendChild(document.createTextNode(after));
      node.parentNode.replaceChild(frag, node);
    });
    const first = root.querySelector('mark');
    if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  fetch('index.md', { cache: 'no-store' })
    .then(r => r.text())
    .then(md => {
      const html = mdToHtml(md);
      el.report.innerHTML = html;
      wrapSections(el.report);
      addSummaryStats(el.report);
      highlightPills(el.report);
      buildSidebar();
      buildTopbar();
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

  // Search events
  let searchTimer = null;
  searchBox && searchBox.addEventListener('input', e => {
    const q = e.target.value.trim();
    if (searchTimer) clearTimeout(searchTimer);
    searchTimer = setTimeout(() => highlightQuery(el.report, q), 180);
  });
})();
