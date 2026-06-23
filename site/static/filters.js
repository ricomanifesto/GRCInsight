(function () {
  function normalize(value) {
    return String(value || '').trim().toLowerCase();
  }

  function normalizedTokens(values) {
    return (values || []).map(normalize).filter(Boolean);
  }

  function stripMetadataLabels(value) {
    return String(value || '').replace(/\b(?:Status|Obligations|Gaps|Deadlines|Owners|Evidence)\s*(?:Detected|Not detected|Action required|Review ready|Needs review|Source referenced|Needs source trail)\b/gi, ' ');
  }

  function ownerSearchTokens(metadata) {
    return metadata.owners === 'Detected' ? 'owner owners owner cues' : '';
  }

  function searchableText(section) {
    const metadata = section.metadata || {};
    return normalize([
      section.title,
      stripMetadataLabels(section.text),
      metadata.reviewStatus,
      metadata.obligations,
      metadata.gaps,
      metadata.deadlines,
      metadata.owners,
      ownerSearchTokens(metadata),
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
    const ownerCue = normalize(active.ownerCue);

    if (query && !searchableText(section).includes(query)) return false;
    if (reviewStatus && reviewStatus !== 'all') {
      if (normalize(section.metadata && section.metadata.reviewStatus) !== reviewStatus) return false;
    }
    if (tagCategory && tagCategory !== 'all') {
      if (!normalizedTokens(section.tagCategories).includes(tagCategory)) return false;
    }
    if (ownerCue && ownerCue !== 'all') {
      const hasOwnerCue = normalize(section.metadata && section.metadata.owners) === 'detected';
      if (ownerCue === 'detected' && !hasOwnerCue) return false;
      if (ownerCue === 'missing' && hasOwnerCue) return false;
    }
    return true;
  }

  function filterSections(sections, filters) {
    return (sections || []).filter(section => sectionMatches(section, filters));
  }

  const allowedReviewStatuses = new Set(['all', 'Action required', 'Review ready', 'Needs review']);
  const allowedTagCategories = new Set(['all', 'framework', 'regulation', 'risk', 'control', 'agency']);
  const allowedOwnerCues = new Set(['all', 'detected', 'missing']);

  function safeValue(value, allowed, fallback) {
    return allowed.has(value) ? value : fallback;
  }

  function parseFilterParams(searchParams) {
    const params = new URLSearchParams(String(searchParams || '').replace(/^\?/, ''));
    return {
      query: String(params.get('q') || '').trim(),
      reviewStatus: safeValue(params.get('status') || 'all', allowedReviewStatuses, 'all'),
      tagCategory: safeValue(params.get('tag') || 'all', allowedTagCategories, 'all'),
      ownerCue: safeValue(params.get('owner') || 'all', allowedOwnerCues, 'all'),
    };
  }

  function buildFilterParams(filters) {
    const active = filters || {};
    const params = new URLSearchParams();
    const query = String(active.query || '').trim();
    const reviewStatus = safeValue(active.reviewStatus || 'all', allowedReviewStatuses, 'all');
    const tagCategory = safeValue(active.tagCategory || 'all', allowedTagCategories, 'all');
    const ownerCue = safeValue(active.ownerCue || 'all', allowedOwnerCues, 'all');
    if (query) params.set('q', query);
    if (reviewStatus !== 'all') params.set('status', reviewStatus);
    if (tagCategory !== 'all') params.set('tag', tagCategory);
    if (ownerCue !== 'all') params.set('owner', ownerCue);
    const serialized = params.toString();
    return serialized ? `?${serialized}` : '';
  }

  function activeFilterLabels(filters) {
    const active = filters || {};
    const labels = [];
    const query = String(active.query || '').trim();
    const reviewStatus = safeValue(active.reviewStatus || 'all', allowedReviewStatuses, 'all');
    const tagCategory = safeValue(active.tagCategory || 'all', allowedTagCategories, 'all');
    const ownerCue = safeValue(active.ownerCue || 'all', allowedOwnerCues, 'all');
    if (query) labels.push(`Search: ${query}`);
    if (reviewStatus !== 'all') labels.push(`Status: ${reviewStatus}`);
    if (tagCategory !== 'all') labels.push(`Tag: ${tagCategory}`);
    if (ownerCue !== 'all') labels.push(`Owner cues: ${ownerCue}`);
    return labels;
  }

  function summarizeFilterResults(matchCount, totalCount, filters) {
    const count = Number(matchCount) || 0;
    const total = Number(totalCount) || 0;
    const labels = activeFilterLabels(filters);
    if (labels.length === 0) return `Showing all ${total} sections`;
    const prefix = count === 0
      ? `No sections match ${labels.length} active ${labels.length === 1 ? 'filter' : 'filters'}`
      : `Showing ${count} of ${total} sections`;
    return [prefix].concat(labels).join(' | ');
  }

  window.GRCInsightFilters = {
    buildFilterParams,
    filterSections,
    normalize,
    parseFilterParams,
    sectionMatches,
    summarizeFilterResults,
  };
})();
