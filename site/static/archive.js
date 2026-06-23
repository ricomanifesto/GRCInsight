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

  function buildReports(markdown) {
    return [
      {
        ...currentReportDefaults,
        ...deriveCurrentReportMetadata(markdown || ''),
      },
    ];
  }

  window.GRCInsightArchive = {
    currentReportId: 'current',
    currentReportDefaults,
    deriveCurrentReportMetadata,
    buildReports,
  };
})();
