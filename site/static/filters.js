(function () {
  function normalize(value) {
    return String(value || '').trim().toLowerCase();
  }

  function normalizedTokens(values) {
    return (values || []).map(normalize).filter(Boolean);
  }

  function searchableText(section) {
    const metadata = section.metadata || {};
    return normalize([
      section.title,
      section.text,
      metadata.reviewStatus,
      metadata.obligations,
      metadata.gaps,
      metadata.deadlines,
      metadata.evidence,
      (section.tagCategories || []).join(' '),
      (section.tagTerms || []).join(' '),
    ].filter(Boolean).join(' '));
  }

  function sectionMatches(section, filters) {
    const active = filters || {};
    const query = normalize(active.query);
    const reviewStatus = normalize(active.reviewStatus);
    const tagCategory = normalize(active.tagCategory);

    if (query && !searchableText(section).includes(query)) return false;
    if (reviewStatus && reviewStatus !== 'all') {
      if (normalize(section.metadata && section.metadata.reviewStatus) !== reviewStatus) return false;
    }
    if (tagCategory && tagCategory !== 'all') {
      if (!normalizedTokens(section.tagCategories).includes(tagCategory)) return false;
    }
    return true;
  }

  function filterSections(sections, filters) {
    return (sections || []).filter(section => sectionMatches(section, filters));
  }

  const allowedReviewStatuses = new Set(['all', 'Action required', 'Review ready', 'Needs review']);
  const allowedTagCategories = new Set(['all', 'framework', 'regulation', 'risk', 'control', 'agency']);

  function safeValue(value, allowed, fallback) {
    return allowed.has(value) ? value : fallback;
  }

  function parseFilterParams(searchParams) {
    const params = new URLSearchParams(String(searchParams || '').replace(/^\?/, ''));
    return {
      query: String(params.get('q') || '').trim(),
      reviewStatus: safeValue(params.get('status') || 'all', allowedReviewStatuses, 'all'),
      tagCategory: safeValue(params.get('tag') || 'all', allowedTagCategories, 'all'),
    };
  }

  function buildFilterParams(filters) {
    const active = filters || {};
    const params = new URLSearchParams();
    const query = String(active.query || '').trim();
    const reviewStatus = safeValue(active.reviewStatus || 'all', allowedReviewStatuses, 'all');
    const tagCategory = safeValue(active.tagCategory || 'all', allowedTagCategories, 'all');
    if (query) params.set('q', query);
    if (reviewStatus !== 'all') params.set('status', reviewStatus);
    if (tagCategory !== 'all') params.set('tag', tagCategory);
    const serialized = params.toString();
    return serialized ? `?${serialized}` : '';
  }

  window.GRCInsightFilters = {
    buildFilterParams,
    filterSections,
    normalize,
    parseFilterParams,
    sectionMatches,
  };
})();
