(function () {
  function escapeHtml(s) {
    return s.replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' })[c]);
  }

  function escapeAttribute(s) {
    return escapeHtml(s).replace(/"/g, '&quot;');
  }

  function sanitizeMarkdownUrl(url) {
    const value = url.trim();
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
    const numberedSectionPattern = /^\d{1,2}[\).]\s+([^\n]+)$/gm;
    return markdown.replace(numberedSectionPattern, (line, title) => {
      const normalizedTitle = title.trim();
      return expectedSectionTitles.has(normalizedTitle) ? `## ${normalizedTitle}` : line;
    });
  }

  window.GRCInsightRenderer = {
    escapeHtml,
    escapeAttribute,
    normalizeReportMarkdown,
    sanitizeMarkdownUrl,
    renderMarkdownLink,
  };
})();
