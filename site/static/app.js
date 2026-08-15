// Progressive enhancements for the pre-rendered GRC briefing. The report is
// complete without JavaScript; this controller adds one contents index, keeps
// the generated date readable, and supports an explicit dark-theme preference.
(function () {
  const reportEl = document.getElementById('report');
  const generatedEl = document.getElementById('generated');
  const themeBtn = document.getElementById('themeToggle');
  const mobileToc = document.getElementById('mobileToc');
  const renderer = window.GRCInsightRenderer;

  let sectionObserver = null;

  function slugify(text) {
    return text.trim().toLowerCase().replace(/[^a-z0-9\s-]/g, '').replace(/\s+/g, '-');
  }

  function setGeneratedLabel(markdown) {
    const match = markdown.match(/\*\*Generated:\*\*\s*(.+)/);
    if (!match || !generatedEl) return;

    const raw = match[1].trim();
    const parsed = new Date(raw);
    const display = isNaN(parsed.getTime())
      ? raw
      : parsed.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        timeZone: 'UTC',
      });

    generatedEl.textContent = `Generated ${display}`;
    generatedEl.setAttribute('datetime', raw);
  }

  function sectionHeadings() {
    return Array.from(reportEl.querySelectorAll('.card h2'));
  }

  function prepareSections() {
    sectionHeadings().forEach(heading => {
      heading.id = heading.id || slugify(heading.textContent);
    });
  }

  function buildNavigation() {
    const toc = document.getElementById('toc');
    const headings = sectionHeadings();
    if (!toc || !headings.length) return;

    toc.innerHTML = headings
      .map(heading => `<a href="#${heading.id}">${renderer.escapeHtml(heading.textContent.trim())}</a>`)
      .join('');

    const links = Array.from(toc.querySelectorAll('a'));
    const linkForHeading = new Map(
      headings.map(heading => [
        heading.id,
        links.find(link => link.getAttribute('href') === `#${heading.id}`),
      ]),
    );

    if (sectionObserver) sectionObserver.disconnect();
    sectionObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        const link = linkForHeading.get(entry.target.id);
        if (!link || !entry.isIntersecting) return;
        links.forEach(item => item.classList.remove('active'));
        link.classList.add('active');
      });
    }, { rootMargin: '0px 0px -70% 0px', threshold: 0.1 });
    headings.forEach(heading => sectionObserver.observe(heading));

    if (mobileToc) {
      mobileToc.innerHTML = '<option value="">Jump to section</option>' + headings
        .map(heading => `<option value="${heading.id}">${renderer.escapeHtml(heading.textContent.trim())}</option>`)
        .join('');
      mobileToc.onchange = event => {
        const target = document.getElementById(event.target.value);
        if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        event.target.value = '';
      };
    }
  }

  function renderReport(markdown) {
    setGeneratedLabel(markdown);
    reportEl.innerHTML = renderer.renderReportDocument(markdown);
    prepareSections();
    buildNavigation();
  }

  const hasPrerenderedReport = reportEl.dataset.prerendered === 'true' && reportEl.querySelector('.card');
  if (hasPrerenderedReport) {
    prepareSections();
    buildNavigation();
  } else {
    reportEl.innerHTML = '<section class="card report-status"><p>Loading report…</p></section>';
  }

  fetch('index.md', { cache: 'no-store' })
    .then(response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.text();
    })
    .then(renderReport)
    .catch(() => {
      if (!hasPrerenderedReport) {
        reportEl.innerHTML = '<section class="card report-status"><p>Unable to load the report. Please refresh to try again.</p></section>';
      }
    });

  function applyTheme(mode) {
    const dark = mode === 'dark';
    document.body.classList.toggle('dark', dark);
    if (!themeBtn) return;

    const next = dark ? 'light' : 'dark';
    themeBtn.textContent = `${next === 'dark' ? 'Dark' : 'Light'} mode`;
    themeBtn.setAttribute('aria-label', `Switch to ${next} theme`);
    themeBtn.title = `Switch to ${next} theme`;
  }

  applyTheme(localStorage.getItem('theme') === 'dark' ? 'dark' : 'light');
  themeBtn && themeBtn.addEventListener('click', () => {
    const next = document.body.classList.contains('dark') ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    applyTheme(next);
  });
})();
