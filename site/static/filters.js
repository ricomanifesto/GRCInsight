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

  const filterStateOptions = Object.freeze([
    Object.freeze({ key: 'query', param: 'q', defaultValue: '', labelPrefix: 'Search' }),
    Object.freeze({ key: 'reviewStatus', param: 'status', defaultValue: 'all', labelPrefix: 'Status' }),
    Object.freeze({ key: 'tagCategory', param: 'tag', defaultValue: 'all', labelPrefix: 'Tag' }),
    Object.freeze({ key: 'ownerCue', param: 'owner', defaultValue: 'all', labelPrefix: 'Owner cues' }),
    Object.freeze({ key: 'evidenceState', param: 'evidence', defaultValue: 'all', labelPrefix: 'Evidence' }),
  ]);
  const filterStateOptionMap = Object.freeze(filterStateOptions.reduce((options, option) => {
    options[option.key] = option;
    return options;
  }, {}));

  function filterStateOption(key) {
    return filterStateOptionMap[key];
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

  function defaultFilterState() {
    return filterStateOptions.reduce((filters, option) => {
      filters[option.key] = option.defaultValue;
      return filters;
    }, {});
  }

  function isDefaultFilterState(filters) {
    const active = filters || {};
    return filterStateOptions.every(option => {
      const value = option.key === 'query'
        ? String(active[option.key] || '').trim()
        : String(active[option.key] || option.defaultValue);
      return value === option.defaultValue;
    });
  }

  function parseFilterParams(searchParams) {
    const params = new URLSearchParams(String(searchParams || '').replace(/^\?/, ''));
    const options = filterStateOptionMap;
    const defaults = defaultFilterState();
    defaults.query = String(params.get(options.query.param) || options.query.defaultValue).trim();
    defaults.reviewStatus = safeValue(params.get(options.reviewStatus.param) || options.reviewStatus.defaultValue, allowedReviewStatusValues(), options.reviewStatus.defaultValue);
    defaults.tagCategory = safeValue(params.get(options.tagCategory.param) || options.tagCategory.defaultValue, allowedTagCategories, options.tagCategory.defaultValue);
    defaults.ownerCue = safeValue(params.get(options.ownerCue.param) || options.ownerCue.defaultValue, allowedOwnerCues, options.ownerCue.defaultValue);
    defaults.evidenceState = safeValue(params.get(options.evidenceState.param) || options.evidenceState.defaultValue, allowedEvidenceStates, options.evidenceState.defaultValue);
    return defaults;
  }

  function buildFilterParams(filters) {
    const active = filters || {};
    const params = new URLSearchParams();
    const options = filterStateOptionMap;
    const query = String(active.query || options.query.defaultValue).trim();
    const reviewStatus = safeValue(active.reviewStatus || options.reviewStatus.defaultValue, allowedReviewStatusValues(), options.reviewStatus.defaultValue);
    const tagCategory = safeValue(active.tagCategory || options.tagCategory.defaultValue, allowedTagCategories, options.tagCategory.defaultValue);
    const ownerCue = safeValue(active.ownerCue || options.ownerCue.defaultValue, allowedOwnerCues, options.ownerCue.defaultValue);
    const evidenceState = safeValue(active.evidenceState || options.evidenceState.defaultValue, allowedEvidenceStates, options.evidenceState.defaultValue);
    if (query) params.set(options.query.param, query);
    if (reviewStatus !== options.reviewStatus.defaultValue) params.set(options.reviewStatus.param, reviewStatus);
    if (tagCategory !== options.tagCategory.defaultValue) params.set(options.tagCategory.param, tagCategory);
    if (ownerCue !== options.ownerCue.defaultValue) params.set(options.ownerCue.param, ownerCue);
    if (evidenceState !== options.evidenceState.defaultValue) params.set(options.evidenceState.param, evidenceState);
    const serialized = params.toString();
    return serialized ? `?${serialized}` : '';
  }

  function activeFilterEntries(filters) {
    const active = filters || {};
    const entries = [];
    const options = filterStateOptionMap;
    const query = String(active.query || options.query.defaultValue).trim();
    const reviewStatus = safeValue(active.reviewStatus || options.reviewStatus.defaultValue, allowedReviewStatusValues(), options.reviewStatus.defaultValue);
    const tagCategory = safeValue(active.tagCategory || options.tagCategory.defaultValue, allowedTagCategories, options.tagCategory.defaultValue);
    const ownerCue = safeValue(active.ownerCue || options.ownerCue.defaultValue, allowedOwnerCues, options.ownerCue.defaultValue);
    const evidenceState = safeValue(active.evidenceState || options.evidenceState.defaultValue, allowedEvidenceStates, options.evidenceState.defaultValue);
    if (query) entries.push({ key: options.query.key, label: `${options.query.labelPrefix}: ${query}` });
    if (reviewStatus !== options.reviewStatus.defaultValue) entries.push({ key: options.reviewStatus.key, label: `${options.reviewStatus.labelPrefix}: ${reviewStatus}` });
    if (tagCategory !== options.tagCategory.defaultValue) entries.push({ key: options.tagCategory.key, label: `${options.tagCategory.labelPrefix}: ${tagCategory}` });
    if (ownerCue !== options.ownerCue.defaultValue) entries.push({ key: options.ownerCue.key, label: `${options.ownerCue.labelPrefix}: ${ownerCue}` });
    if (evidenceState !== options.evidenceState.defaultValue) entries.push({ key: options.evidenceState.key, label: `${options.evidenceState.labelPrefix}: ${evidenceState}` });
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
    defaultFilterState,
    evidenceStateValues,
    filterStateOption,
    filterStateOptionMap,
    filterStateOptions,
    filterSections,
    isDefaultFilterState,
    normalize,
    parseFilterParams,
    sectionMatches,
    setMetadataStates,
    setReviewStatusOptions,
    statusQuickFilterCounts,
    summarizeFilterResults,
  };
})();
