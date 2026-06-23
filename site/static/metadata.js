(function () {
  const evidencePattern = /\b(source|sources|evidence|articles analyzed|osint|dpia|certification)\b/i;
  const obligationPattern = /\b(must|required|requires|requirement|mandatory|enforcement|deadline|shall|conduct|implement|validate|update|establish)\b/i;
  const gapPattern = /\b(gap|gaps|lapsed|unresolved|finding|findings|non-compliance|exposure|underassessed|unknown|absence)\b/i;
  const deadlinePattern = /\b(deadline|due|within|0.{0,3}30|30.{0,3}90|90.{0,3}180|days|weekly|monthly|quarterly|immediate|begins|passed|q[1-4]\s+\d{4})\b/i;
  const actionPattern = /\b(action|priority|owner|remediation|implement|conduct|validate|update|establish)\b/i;
  const ownerPattern = /\b(owner|owners|owned by|accountable|accountability|responsible|assigned to)\b/i;

  function detected(pattern, value) {
    return pattern.test(value);
  }

  function deriveSectionMetadata(title, text) {
    const content = `${title || ''} ${text || ''}`.trim();
    const hasEvidence = detected(evidencePattern, content);
    const hasObligations = detected(obligationPattern, content);
    const hasGaps = detected(gapPattern, content);
    const hasDeadlines = detected(deadlinePattern, content);
    const hasActions = detected(actionPattern, content);
    const hasOwners = detected(ownerPattern, content);

    let reviewStatus = 'Needs review';
    if (hasActions || hasObligations || hasGaps || hasDeadlines) {
      reviewStatus = 'Action required';
    } else if (hasEvidence) {
      reviewStatus = 'Review ready';
    }

    return {
      reviewStatus,
      obligations: hasObligations ? 'Detected' : 'Not detected',
      gaps: hasGaps ? 'Detected' : 'Not detected',
      deadlines: hasDeadlines ? 'Detected' : 'Not detected',
      owners: hasOwners ? 'Detected' : 'Not detected',
      evidence: hasEvidence ? 'Source referenced' : 'Needs source trail',
    };
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>]/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
    })[c]);
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/"/g, c => ({
      '"': '&quot;',
    })[c]);
  }

  function renderSectionMetadata(metadata) {
    const rows = [
      ['Status', metadata.reviewStatus],
      ['Obligations', metadata.obligations],
      ['Gaps', metadata.gaps],
      ['Deadlines', metadata.deadlines],
      ['Owners', metadata.owners],
      ['Evidence', metadata.evidence],
    ];
    const items = rows.map(([label, value]) =>
      `<span class="section-meta-item"><span class="section-meta-label">${escapeHtml(label)}</span><span>${escapeHtml(value)}</span></span>`
    ).join('');
    return `<div class="section-meta" data-review-status="${escapeAttribute(metadata.reviewStatus)}" data-obligations="${escapeAttribute(metadata.obligations)}" data-gaps="${escapeAttribute(metadata.gaps)}" data-deadlines="${escapeAttribute(metadata.deadlines)}" data-owners="${escapeAttribute(metadata.owners)}" data-evidence="${escapeAttribute(metadata.evidence)}">${items}</div>`;
  }

  function countByValue(sections, field, value) {
    return sections.filter(section => section.metadata && section.metadata[field] === value).length;
  }

  function summarizeSections(sections) {
    const normalized = Array.isArray(sections) ? sections : [];
    const gapTitles = normalized
      .filter(section => section.metadata && section.metadata.evidence === 'Needs source trail')
      .map(section => section.title || 'Untitled section');
    const evidenceTitles = normalized
      .filter(section => section.metadata && section.metadata.evidence === 'Source referenced')
      .map(section => section.title || 'Untitled section');
    const actionTitles = normalized
      .filter(section => section.metadata && section.metadata.reviewStatus === 'Action required')
      .map(section => section.title || 'Untitled section');
    const ownerTitles = normalized
      .filter(section => section.metadata && section.metadata.owners === 'Detected')
      .map(section => section.title || 'Untitled section');
    const evidenceGaps = gapTitles.length;
    return {
      totalSections: normalized.length,
      actionRequired: countByValue(normalized, 'reviewStatus', 'Action required'),
      reviewReady: countByValue(normalized, 'reviewStatus', 'Review ready'),
      needsReview: countByValue(normalized, 'reviewStatus', 'Needs review'),
      obligations: countByValue(normalized, 'obligations', 'Detected'),
      gaps: countByValue(normalized, 'gaps', 'Detected'),
      deadlines: countByValue(normalized, 'deadlines', 'Detected'),
      owners: countByValue(normalized, 'owners', 'Detected'),
      evidenceReady: countByValue(normalized, 'evidence', 'Source referenced'),
      evidenceGaps,
      auditReady: normalized.length > 0 && evidenceGaps === 0 && countByValue(normalized, 'reviewStatus', 'Needs review') === 0,
      gapTitles,
      evidenceTitles,
      actionTitles,
      ownerTitles,
    };
  }

  function renderList(items, emptyText) {
    if (!items.length) return `<li>${escapeHtml(emptyText)}</li>`;
    return items.slice(0, 4).map(item => `<li>${escapeHtml(item)}</li>`).join('');
  }

  function renderAuditSummary(summary) {
    const readiness = summary.auditReady ? 'Audit-ready' : 'Needs source trail';
    return `
      <div class="audit-summary-card">
        <div>
          <p class="audit-kicker">Audit-ready summary</p>
          <h2>${escapeHtml(readiness)}</h2>
          <p class="audit-summary-copy">${summary.totalSections} sections reviewed for obligations, gaps, deadlines, and evidence trails.</p>
        </div>
        <div class="audit-metrics">
          <span><strong>${summary.actionRequired}</strong> action required</span>
          <span><strong>${summary.obligations}</strong> obligations</span>
          <span><strong>${summary.gaps}</strong> gaps</span>
          <span><strong>${summary.deadlines}</strong> deadlines</span>
          <span><strong>${summary.owners}</strong> owner cues</span>
          <span><strong>${summary.evidenceGaps}</strong> source-trail gaps</span>
        </div>
        <div class="audit-lists">
          <div>
            <h3>Action focus</h3>
            <ul>${renderList(summary.actionTitles, 'No action-required sections detected')}</ul>
          </div>
          <div>
            <h3>Evidence trail</h3>
            <ul>${renderList(summary.evidenceTitles, 'No source-backed sections detected')}</ul>
          </div>
          <div>
            <h3>Owner cues</h3>
            <ul>${renderList(summary.ownerTitles, 'No owner cues detected')}</ul>
          </div>
          <div>
            <h3>Evidence gaps</h3>
            <ul>${renderList(summary.gapTitles, 'No missing source trails detected')}</ul>
          </div>
        </div>
      </div>
    `;
  }

  window.GRCInsightMetadata = {
    deriveSectionMetadata,
    renderSectionMetadata,
    summarizeSections,
    renderAuditSummary,
  };
})();
