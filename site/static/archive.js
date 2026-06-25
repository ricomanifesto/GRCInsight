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
    const provenanceSummary = context.provenanceSummary || {};
    const totalSections = Number(summary.totalSections) || 0;
    const actionRequired = Number(summary.actionRequired) || 0;
    const sourceGaps = Number(provenanceSummary.sourceGaps) || 0;
    const tagCategories = Array.from(new Set(context.tagCategories || []));
    if (!totalSections && !tagCategories.length) return [];
    return [
      {
        label: 'Sections',
        value: String(totalSections),
        state: totalSections ? 'ready' : 'empty',
      },
      {
        label: 'Action required',
        value: String(actionRequired),
        state: actionRequired ? 'attention' : 'ready',
      },
      {
        label: 'Evidence ready',
        value: provenanceSummary.value || 'No data',
        state: provenanceSummary.state || 'empty',
      },
      {
        label: 'Source-trail gaps',
        value: totalSections ? String(sourceGaps) : 'No data',
        state: sourceGaps ? 'gap' : (totalSections ? 'ready' : 'empty'),
      },
      {
        label: 'Tag categories',
        value: String(tagCategories.length),
        state: tagCategories.length ? 'ready' : 'empty',
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
  };
})();
