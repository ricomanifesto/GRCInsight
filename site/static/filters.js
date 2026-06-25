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

  const defaultMetadataStates = Object.freeze({
    detection: Object.freeze({
      detected: 'Detected',
      notDetected: 'Not detected',
    }),
    evidence: Object.freeze({
      sourceReferenced: 'Source referenced',
      needsSourceTrail: 'Needs source trail',
    }),
  });
  let metadataStates = defaultMetadataStates;

  function normalizeMetadataStates(states) {
    const source = states || {};
    const detection = source.detection || {};
    const evidence = source.evidence || {};
    return {
      detection: {
        detected: String(detection.detected || defaultMetadataStates.detection.detected).trim(),
        notDetected: String(detection.notDetected || defaultMetadataStates.detection.notDetected).trim(),
      },
      evidence: {
        sourceReferenced: String(evidence.sourceReferenced || defaultMetadataStates.evidence.sourceReferenced).trim(),
        needsSourceTrail: String(evidence.needsSourceTrail || defaultMetadataStates.evidence.needsSourceTrail).trim(),
      },
    };
  }

  function setMetadataStates(states) {
    metadataStates = normalizeMetadataStates(states);
  }

  function evidenceStateValues() {
    return ['all', 'referenced', 'missing'];
  }

  function ownerSearchTokens(metadata) {
    return metadata.owners === metadataStates.detection.detected ? 'owner owners owner cues' : '';
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
    const evidenceState = normalize(active.evidenceState);

    if (query && !searchableText(section).includes(query)) return false;
    if (reviewStatus && reviewStatus !== 'all') {
      if (normalize(section.metadata && section.metadata.reviewStatus) !== reviewStatus) return false;
    }
    if (tagCategory && tagCategory !== 'all') {
      if (!normalizedTokens(section.tagCategories).includes(tagCategory)) return false;
    }
    if (ownerCue && ownerCue !== 'all') {
      const hasOwnerCue = normalize(section.metadata && section.metadata.owners) === normalize(metadataStates.detection.detected);
      if (ownerCue === 'detected' && !hasOwnerCue) return false;
      if (ownerCue === 'missing' && hasOwnerCue) return false;
    }
    if (evidenceState && evidenceState !== 'all') {
      const hasEvidence = normalize(section.metadata && section.metadata.evidence) === normalize(metadataStates.evidence.sourceReferenced);
      if (evidenceState === 'referenced' && !hasEvidence) return false;
      if (evidenceState === 'missing' && hasEvidence) return false;
    }
    return true;
  }

  function filterSections(sections, filters) {
    return (sections || []).filter(section => sectionMatches(section, filters));
  }

  const defaultReviewStatusOptions = Object.freeze([
    Object.freeze({ value: 'Action required', label: 'Action' }),
    Object.freeze({ value: 'Review ready', label: 'Ready' }),
    Object.freeze({ value: 'Needs review', label: 'Needs review' }),
  ]);
  let reviewStatusOptions = defaultReviewStatusOptions.slice();

  function normalizeReviewStatusOptions(options) {
    const normalized = (Array.isArray(options) ? options : [])
      .map(option => ({
        value: String(option && option.value || '').trim(),
        label: String(option && option.label || option && option.value || '').trim(),
      }))
      .filter(option => option.value);
    return normalized.length ? normalized : defaultReviewStatusOptions.slice();
  }

  function reviewStatusValues() {
    return reviewStatusOptions.map(option => option.value);
  }

  function allowedReviewStatusValues() {
    return ['all'].concat(reviewStatusValues());
  }

  function setReviewStatusOptions(options) {
    reviewStatusOptions = normalizeReviewStatusOptions(options);
  }

  function statusQuickFilterCounts(sections, filters) {
    const active = filters || {};
    const counts = reviewStatusValues().reduce((accumulator, value) => {
      accumulator[value] = 0;
      return accumulator;
    }, {});
    (sections || []).forEach(section => {
      const status = section.metadata && section.metadata.reviewStatus;
      if (!Object.prototype.hasOwnProperty.call(counts, status)) return;
      if (sectionMatches(section, Object.assign({}, active, { reviewStatus: 'all' }))) {
        counts[status] += 1;
      }
    });
    return counts;
  }

  const allowedTagCategories = new Set(['all', 'framework', 'regulation', 'risk', 'control', 'agency']);
  const allowedOwnerCues = new Set(['all', 'detected', 'missing']);
  const allowedEvidenceStates = new Set(evidenceStateValues());

  function safeValue(value, allowed, fallback) {
    return allowed.includes ? (allowed.includes(value) ? value : fallback) : (allowed.has(value) ? value : fallback);
  }

  function parseFilterParams(searchParams) {
    const params = new URLSearchParams(String(searchParams || '').replace(/^\?/, ''));
    return {
      query: String(params.get('q') || '').trim(),
      reviewStatus: safeValue(params.get('status') || 'all', allowedReviewStatusValues(), 'all'),
      tagCategory: safeValue(params.get('tag') || 'all', allowedTagCategories, 'all'),
      ownerCue: safeValue(params.get('owner') || 'all', allowedOwnerCues, 'all'),
      evidenceState: safeValue(params.get('evidence') || 'all', allowedEvidenceStates, 'all'),
    };
  }

  function buildFilterParams(filters) {
    const active = filters || {};
    const params = new URLSearchParams();
    const query = String(active.query || '').trim();
    const reviewStatus = safeValue(active.reviewStatus || 'all', allowedReviewStatusValues(), 'all');
    const tagCategory = safeValue(active.tagCategory || 'all', allowedTagCategories, 'all');
    const ownerCue = safeValue(active.ownerCue || 'all', allowedOwnerCues, 'all');
    const evidenceState = safeValue(active.evidenceState || 'all', allowedEvidenceStates, 'all');
    if (query) params.set('q', query);
    if (reviewStatus !== 'all') params.set('status', reviewStatus);
    if (tagCategory !== 'all') params.set('tag', tagCategory);
    if (ownerCue !== 'all') params.set('owner', ownerCue);
    if (evidenceState !== 'all') params.set('evidence', evidenceState);
    const serialized = params.toString();
    return serialized ? `?${serialized}` : '';
  }

  function activeFilterEntries(filters) {
    const active = filters || {};
    const entries = [];
    const query = String(active.query || '').trim();
    const reviewStatus = safeValue(active.reviewStatus || 'all', allowedReviewStatusValues(), 'all');
    const tagCategory = safeValue(active.tagCategory || 'all', allowedTagCategories, 'all');
    const ownerCue = safeValue(active.ownerCue || 'all', allowedOwnerCues, 'all');
    const evidenceState = safeValue(active.evidenceState || 'all', allowedEvidenceStates, 'all');
    if (query) entries.push({ key: 'query', label: `Search: ${query}` });
    if (reviewStatus !== 'all') entries.push({ key: 'reviewStatus', label: `Status: ${reviewStatus}` });
    if (tagCategory !== 'all') entries.push({ key: 'tagCategory', label: `Tag: ${tagCategory}` });
    if (ownerCue !== 'all') entries.push({ key: 'ownerCue', label: `Owner cues: ${ownerCue}` });
    if (evidenceState !== 'all') entries.push({ key: 'evidenceState', label: `Evidence: ${evidenceState}` });
    return entries;
  }

  function activeFilterLabels(filters) {
    return activeFilterEntries(filters).map(entry => entry.label);
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
    activeFilterEntries,
    activeFilterLabels,
    allowedReviewStatusValues,
    buildFilterParams,
    evidenceStateValues,
    filterSections,
    normalize,
    parseFilterParams,
    sectionMatches,
    setMetadataStates,
    setReviewStatusOptions,
    statusQuickFilterCounts,
    summarizeFilterResults,
  };
})();
