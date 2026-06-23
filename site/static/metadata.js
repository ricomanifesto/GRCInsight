(function () {
  const evidencePattern = /\b(source|sources|evidence|articles analyzed|osint|dpia|certification)\b/i;
  const obligationPattern = /\b(must|required|requires|requirement|mandatory|enforcement|deadline|shall|conduct|implement|validate|update|establish)\b/i;
  const gapPattern = /\b(gap|gaps|lapsed|unresolved|finding|findings|non-compliance|exposure|underassessed|unknown|absence)\b/i;
  const deadlinePattern = /\b(deadline|due|within|0.{0,3}30|30.{0,3}90|90.{0,3}180|days|weekly|monthly|quarterly|immediate|begins|passed|q[1-4]\s+\d{4})\b/i;
  const actionPattern = /\b(action|priority|owner|remediation|implement|conduct|validate|update|establish)\b/i;

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
      evidence: hasEvidence ? 'Source referenced' : 'Needs source trail',
    };
  }

  function escapeAttribute(value) {
    return String(value).replace(/[&<>"]/g, c => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
    })[c]);
  }

  function renderSectionMetadata(metadata) {
    const rows = [
      ['Status', metadata.reviewStatus],
      ['Obligations', metadata.obligations],
      ['Gaps', metadata.gaps],
      ['Deadlines', metadata.deadlines],
      ['Evidence', metadata.evidence],
    ];
    const items = rows.map(([label, value]) =>
      `<span class="section-meta-item"><span class="section-meta-label">${label}</span><span>${value}</span></span>`
    ).join('');
    return `<div class="section-meta" data-review-status="${escapeAttribute(metadata.reviewStatus)}">${items}</div>`;
  }

  window.GRCInsightMetadata = {
    deriveSectionMetadata,
    renderSectionMetadata,
  };
})();
