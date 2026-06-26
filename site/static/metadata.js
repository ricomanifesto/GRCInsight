(function () {
  const evidencePattern = /\b(source|sources|evidence|articles analyzed|osint|dpia|certification)\b/i;
  const obligationPattern = /\b(must|required|requires|requirement|mandatory|enforcement|deadline|shall|conduct|implement|validate|update|establish)\b/i;
  const gapPattern = /\b(gap|gaps|lapsed|unresolved|finding|findings|non-compliance|exposure|underassessed|unknown|absence)\b/i;
  const deadlinePattern = /\b(deadline|due|within|0.{0,3}30|30.{0,3}90|90.{0,3}180|days|weekly|monthly|quarterly|immediate|begins|passed|q[1-4]\s+\d{4})\b/i;
  const actionPattern = /\b(action|priority|owner|remediation|implement|conduct|validate|update|establish)\b/i;
  const ownerPattern = /\b(owner|owners|owned by|accountable|accountability|responsible|assigned to)\b/i;
  const reviewStatusOptions = Object.freeze([
    Object.freeze({ value: 'Action required', label: 'Action' }),
    Object.freeze({ value: 'Review ready', label: 'Ready' }),
    Object.freeze({ value: 'Needs review', label: 'Needs review' }),
  ]);
  const REVIEW_STATUS = Object.freeze({
    actionRequired: reviewStatusOptions[0].value,
    reviewReady: reviewStatusOptions[1].value,
    needsReview: reviewStatusOptions[2].value,
  });
  const metadataStates = Object.freeze({
    detection: Object.freeze({
      detected: 'Detected',
      notDetected: 'Not detected',
    }),
    evidence: Object.freeze({
      sourceReferenced: 'Source referenced',
      needsSourceTrail: 'Needs source trail',
    }),
  });
  const reviewSignalStates = Object.freeze({
    ready: 'ready',
    gap: 'gap',
    empty: 'empty',
    attention: 'attention',
  });

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

    let reviewStatus = REVIEW_STATUS.needsReview;
    if (hasActions || hasObligations || hasGaps || hasDeadlines) {
      reviewStatus = REVIEW_STATUS.actionRequired;
    } else if (hasEvidence) {
      reviewStatus = REVIEW_STATUS.reviewReady;
    }

    return {
      reviewStatus,
      obligations: hasObligations ? metadataStates.detection.detected : metadataStates.detection.notDetected,
      gaps: hasGaps ? metadataStates.detection.detected : metadataStates.detection.notDetected,
      deadlines: hasDeadlines ? metadataStates.detection.detected : metadataStates.detection.notDetected,
      owners: hasOwners ? metadataStates.detection.detected : metadataStates.detection.notDetected,
      evidence: hasEvidence ? metadataStates.evidence.sourceReferenced : metadataStates.evidence.needsSourceTrail,
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
      .filter(section => section.metadata && section.metadata.evidence === metadataStates.evidence.needsSourceTrail)
      .map(section => section.title || 'Untitled section');
    const evidenceTitles = normalized
      .filter(section => section.metadata && section.metadata.evidence === metadataStates.evidence.sourceReferenced)
      .map(section => section.title || 'Untitled section');
    const actionTitles = normalized
      .filter(section => section.metadata && section.metadata.reviewStatus === REVIEW_STATUS.actionRequired)
      .map(section => section.title || 'Untitled section');
    const ownerTitles = normalized
      .filter(section => section.metadata && section.metadata.owners === metadataStates.detection.detected)
      .map(section => section.title || 'Untitled section');
    const evidenceGaps = gapTitles.length;
    return {
      totalSections: normalized.length,
      actionRequired: countByValue(normalized, 'reviewStatus', REVIEW_STATUS.actionRequired),
      reviewReady: countByValue(normalized, 'reviewStatus', REVIEW_STATUS.reviewReady),
      needsReview: countByValue(normalized, 'reviewStatus', REVIEW_STATUS.needsReview),
      obligations: countByValue(normalized, 'obligations', metadataStates.detection.detected),
      gaps: countByValue(normalized, 'gaps', metadataStates.detection.detected),
      deadlines: countByValue(normalized, 'deadlines', metadataStates.detection.detected),
      owners: countByValue(normalized, 'owners', metadataStates.detection.detected),
      evidenceReady: countByValue(normalized, 'evidence', metadataStates.evidence.sourceReferenced),
      evidenceGaps,
      auditReady: normalized.length > 0 && evidenceGaps === 0 && countByValue(normalized, 'reviewStatus', REVIEW_STATUS.needsReview) === 0,
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

  function buildProvenanceSummary(summary) {
    const normalized = summary || {};
    const total = normalized.totalSections || 0;
    if (total <= 0) {
      return {
        totalSections: 0,
        sourceReady: 0,
        sourceGaps: 0,
        value: 'No data',
        state: reviewSignalStates.empty,
        note: 'No generated sections available for provenance review.',
      };
    }
    const sourceReady = normalized.evidenceReady || 0;
    const evidenceGaps = normalized.evidenceGaps || 0;
    return {
      totalSections: total,
      sourceReady,
      sourceGaps: evidenceGaps,
      value: `${sourceReady}/${total}`,
      state: evidenceGaps === 0 ? reviewSignalStates.ready : reviewSignalStates.gap,
      note: evidenceGaps
        ? `${evidenceGaps} sections still need source trails.`
        : 'Every visible section includes source evidence language.',
    };
  }

  function sourceProvenanceCoverageRow(summary) {
    const provenance = buildProvenanceSummary(summary);
    return {
      label: 'Source provenance',
      value: provenance.value,
      state: provenance.state,
      note: provenance.note,
    };
  }

  function coverageMetricEntries(summary) {
    const total = summary.totalSections || 0;
    const obligationSignals = summary.obligations || 0;
    const gapSignals = summary.gaps || 0;
    const deadlineSignals = summary.deadlines || 0;
    const emptyNote = 'No visible sections are available for this coverage check.';
    if (!total) {
      return [
        {
          key: 'generatedSections',
          label: 'Generated sections',
          value: '0',
          state: reviewSignalStates.empty,
          note: 'No generated sections match the active filters.',
        },
        {
          key: 'sourceProvenance',
          ...sourceProvenanceCoverageRow(summary),
        },
        {
          key: 'obligations',
          label: 'Obligations',
          value: 'No data',
          state: reviewSignalStates.empty,
          note: emptyNote,
        },
        {
          key: 'ownershipCues',
          label: 'Ownership cues',
          value: 'No data',
          state: reviewSignalStates.empty,
          note: emptyNote,
        },
        {
          key: 'gapsAndDeadlines',
          label: 'Gaps and deadlines',
          value: 'No data',
          state: reviewSignalStates.empty,
          note: emptyNote,
        },
      ];
    }
    return [
      {
        key: 'generatedSections',
        label: 'Generated sections',
        value: String(total),
        state: reviewSignalStates.ready,
        note: 'Rendered report sections available for review.',
      },
      {
        key: 'sourceProvenance',
        ...sourceProvenanceCoverageRow(summary),
      },
      {
        key: 'obligations',
        label: 'Obligations',
        value: String(obligationSignals),
        state: obligationSignals ? reviewSignalStates.attention : reviewSignalStates.empty,
        note: obligationSignals ? 'Mandatory or required-action language detected.' : 'No obligation language detected in visible sections.',
      },
      {
        key: 'ownershipCues',
        label: 'Ownership cues',
        value: String(summary.owners || 0),
        state: summary.owners ? reviewSignalStates.ready : reviewSignalStates.gap,
        note: summary.owners ? 'At least one section names accountability cues.' : 'No explicit owner cues detected.',
      },
      {
        key: 'gapsAndDeadlines',
        label: 'Gaps and deadlines',
        value: String(gapSignals + deadlineSignals),
        state: (gapSignals || deadlineSignals) ? reviewSignalStates.attention : reviewSignalStates.ready,
        note: (gapSignals || deadlineSignals)
          ? `${gapSignals} gap signals and ${deadlineSignals} deadline signals need review.`
          : 'No gap or deadline signals detected in visible sections.',
      },
    ];
  }

  function coverageRows(summary) {
    return coverageMetricEntries(summary);
  }

  function renderCoverageTable(summary) {
    const rows = coverageMetricEntries(summary).map(row => `
      <tr class="coverage-row" data-coverage-state="${escapeAttribute(row.state)}">
        <th scope="row">${escapeHtml(row.label)}</th>
        <td><strong>${escapeHtml(row.value)}</strong></td>
        <td>${escapeHtml(row.note)}</td>
      </tr>
    `).join('');
    return `
      <div class="coverage-table">
        <table>
          <caption>Coverage matrix</caption>
          <thead>
            <tr>
              <th scope="col">Contract</th>
              <th scope="col">Coverage</th>
              <th scope="col">Review note</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function auditSummaryMetricEntries(summary) {
    const normalized = summary || {};
    return [
      {
        key: 'actionRequired',
        label: 'action required',
        value: String(normalized.actionRequired || 0),
      },
      {
        key: 'obligations',
        label: 'obligations',
        value: String(normalized.obligations || 0),
      },
      {
        key: 'gaps',
        label: 'gaps',
        value: String(normalized.gaps || 0),
      },
      {
        key: 'deadlines',
        label: 'deadlines',
        value: String(normalized.deadlines || 0),
      },
      {
        key: 'owners',
        label: 'owner cues',
        value: String(normalized.owners || 0),
      },
      {
        key: 'evidenceGaps',
        label: 'source-trail gaps',
        value: String(normalized.evidenceGaps || 0),
      },
    ];
  }

  function renderAuditSummaryMetrics(summary) {
    return auditSummaryMetricEntries(summary).map(row =>
      `<span><strong>${escapeHtml(row.value)}</strong> ${escapeHtml(row.label)}</span>`
    ).join('');
  }

  function renderWorkspaceOverview(summary) {
    const readiness = summary.totalSections === 0
      ? 'No generated sections match the active filters'
      : (summary.auditReady ? 'Audit-ready visible set' : 'Compliance review workspace');
    return `
      <div class="workspace-overview-card">
        <div class="workspace-heading-block">
          <p class="workspace-kicker">Generated compliance archive</p>
          <h2>${escapeHtml(readiness)}</h2>
          <p class="workspace-copy">${summary.totalSections} visible sections mapped across obligations, controls, gaps, owner cues, and source provenance.</p>
        </div>
        <div class="workspace-actions" aria-label="Workspace actions">
          <a href="#auditSummary">Audit summary</a>
          <a href="#report">Generated sections</a>
          <a href="#toc">Section index</a>
        </div>
        ${renderCoverageTable(summary)}
      </div>
    `;
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
          ${renderAuditSummaryMetrics(summary)}
        </div>
        ${renderCoverageTable(summary)}
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
    auditSummaryMetricEntries,
    buildProvenanceSummary,
    coverageMetricEntries,
    coverageRows,
    deriveSectionMetadata,
    metadataStates,
    renderSectionMetadata,
    renderWorkspaceOverview,
    reviewSignalStates,
    reviewStatusOptions,
    summarizeSections,
    renderAuditSummary,
  };
})();
