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

  window.GRCInsightFilters = {
    filterSections,
    normalize,
    sectionMatches,
  };
})();
