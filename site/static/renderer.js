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

  window.GRCInsightRenderer = {
    escapeHtml,
    escapeAttribute,
    sanitizeMarkdownUrl,
    renderMarkdownLink,
  };
})();
