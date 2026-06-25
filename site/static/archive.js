(function () {
  const currentReportDefaults = {
    id: 'current',
    href: 'index.html',
    status: 'Current',
    summary: 'Executive briefing covering regulatory enforcement, privacy obligations, framework shifts, and risk priorities.',
    tags: ['GRC', 'NIST', 'PCI-DSS', 'GDPR', 'Privacy', 'Risk'],
    highlights: [
      'Governance and control expectations are tracked from the generated report content.',
      'Regulatory and risk priorities stay tied to the current report snapshot.',
    ],
  };
  const defaultReviewSignalStates = Object.freeze({
    ready: 'ready',
    gap: 'gap',
    empty: 'empty',
    attention: 'attention',
  });
  let reviewSignalStates = defaultReviewSignalStates;

  function normalizeReviewSignalStates(states) {
    const source = states || {};
    return {
      ready: String(source.ready || defaultReviewSignalStates.ready).trim(),
      gap: String(source.gap || defaultReviewSignalStates.gap).trim(),
      empty: String(source.empty || defaultReviewSignalStates.empty).trim(),
      attention: String(source.attention || defaultReviewSignalStates.attention).trim(),
    };
  }

  function setReviewSignalStates(states) {
    reviewSignalStates = normalizeReviewSignalStates(states);
  }

  function extractTableValue(markdown, label) {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const pattern = new RegExp(`^\\|\\s*\\*\\*${escaped}\\*\\*\\s*\\|\\s*([^|]+?)\\s*\\|`, 'im');
    const match = markdown.match(pattern);
    return match ? match[1].trim() : '';
  }

  function deriveCurrentReportMetadata(markdown) {
    const titleMatch = markdown.match(/^#\s+(.+)$/m);
    const generatedMatch = markdown.match(/^\*\*Generated:\*\*\s*(.+)$/m);
    const period = extractTableValue(markdown, 'Report Period');
    return {
      title: titleMatch ? titleMatch[1].trim() : 'GRC Intelligence Report',
      generatedAt: generatedMatch ? generatedMatch[1].trim() : '',
      period: period || 'Current period',
    };
  }

  function buildReviewMetrics(reviewContext) {
    const context = reviewContext || {};
    const summary = context.summary || {};
    const totalSections = Number(summary.totalSections) || 0;
    const actionRequired = Number(summary.actionRequired) || 0;
    const evidenceReady = Number(summary.evidenceReady) || 0;
    const evidenceGaps = Number(summary.evidenceGaps) || 0;
    const provenanceSummary = context.provenanceSummary || {
      value: totalSections ? `${evidenceReady}/${totalSections}` : 'No data',
      state: totalSections && evidenceGaps === 0
        ? reviewSignalStates.ready
        : (totalSections ? reviewSignalStates.gap : reviewSignalStates.empty),
      sourceGaps: evidenceGaps,
    };
    const sourceGaps = Number(provenanceSummary.sourceGaps) || 0;
    const tagCategories = Array.from(new Set(context.tagCategories || []));
    if (!totalSections && !tagCategories.length) return [];
    return [
      {
        label: 'Sections',
        value: String(totalSections),
        state: totalSections ? reviewSignalStates.ready : reviewSignalStates.empty,
      },
      {
        label: 'Action required',
        value: String(actionRequired),
        state: actionRequired ? reviewSignalStates.attention : reviewSignalStates.ready,
      },
      {
        label: 'Evidence ready',
        value: provenanceSummary.value || 'No data',
        state: provenanceSummary.state || reviewSignalStates.empty,
      },
      {
        label: 'Source-trail gaps',
        value: totalSections ? String(sourceGaps) : 'No data',
        state: sourceGaps
          ? reviewSignalStates.gap
          : (totalSections ? reviewSignalStates.ready : reviewSignalStates.empty),
      },
      {
        label: 'Tag categories',
        value: String(tagCategories.length),
        state: tagCategories.length ? reviewSignalStates.ready : reviewSignalStates.empty,
      },
    ];
  }

  function buildReports(markdown, reviewContext) {
    return [
      {
        ...currentReportDefaults,
        ...deriveCurrentReportMetadata(markdown || ''),
        reviewMetrics: buildReviewMetrics(reviewContext),
      },
    ];
  }

  window.GRCInsightArchive = {
    currentReportId: 'current',
    currentReportDefaults,
    buildReviewMetrics,
    deriveCurrentReportMetadata,
    buildReports,
    setReviewSignalStates,
  };
})();
