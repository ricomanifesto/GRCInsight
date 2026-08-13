(function () {
  const categories = [
    {
      key: 'frameworks',
      label: 'Frameworks',
      pillClass: 'framework',
      terms: [
        {
          label: 'ISO/IEC 27001:2022',
          aliases: ['ISO/IEC 27001:2022', 'ISO/IEC 27001', 'ISO 27001'],
          url: 'https://www.iso.org/standard/27001',
        },
        {
          label: 'NIST CSF 2.0',
          aliases: ['NIST Cybersecurity Framework 2.0', 'NIST CSF 2.0', 'NIST CSF', 'NIST'],
          url: 'https://www.nist.gov/cyberframework',
        },
        {
          label: 'NIST SP 800-207',
          aliases: ['NIST SP 800-207', 'SP 800-207'],
          url: 'https://csrc.nist.gov/pubs/sp/800/207/final',
        },
        {
          label: 'COBIT',
          aliases: ['COBIT'],
          url: 'https://www.isaca.org/resources/cobit',
        },
        {
          label: 'COSO',
          aliases: ['COSO'],
          url: 'https://www.coso.org/guidance-on-ic/pages/default.aspx',
        },
        {
          label: 'PCI DSS',
          aliases: ['PCI DSS', 'PCI-DSS'],
          url: 'https://www.pcisecuritystandards.org/standards/pci-dss/',
        },
      ],
    },
    {
      key: 'regulations',
      label: 'Regulations',
      pillClass: 'regulation',
      terms: [
        {
          label: 'GDPR',
          aliases: ['GDPR'],
          url: 'https://eur-lex.europa.eu/eli/reg/2016/679/oj',
        },
        {
          label: 'CCPA',
          aliases: ['CCPA'],
          url: 'https://cppa.ca.gov/regulations/consumer_privacy_act.html',
        },
        {
          label: 'SOX',
          aliases: ['Sarbanes-Oxley', 'SOX'],
          url: 'https://www.sec.gov/rules-regulations/statutes-regulations',
        },
        {
          label: 'HIPAA',
          aliases: ['HIPAA'],
          url: 'https://www.hhs.gov/hipaa/for-professionals/index.html',
        },
      ],
    },
    {
      key: 'agencies',
      label: 'Agencies',
      pillClass: 'agency',
      terms: [
        { label: 'SEC', aliases: ['SEC'], url: 'https://www.sec.gov/about' },
        { label: 'FTC', aliases: ['FTC'], url: 'https://www.ftc.gov/' },
        { label: 'HHS', aliases: ['HHS'], url: 'https://www.hhs.gov/' },
        { label: 'CISA', aliases: ['CISA'], url: 'https://www.cisa.gov/' },
        { label: 'CPPA', aliases: ['CPPA'], url: 'https://cppa.ca.gov/' },
        { label: 'FFIEC', aliases: ['FFIEC'], url: 'https://www.ffiec.gov/' },
      ],
    },
  ];

  // These substitutions keep offsets stable, allowing matches against a
  // normalized copy while preserving the report's original visible text.
  function normalizeComplianceText(value) {
    return String(value)
      .replace(/[\u00a0\u2007\u2009\u202f]/g, ' ')
      .replace(/[\u2010-\u2015\u2212]/g, '-')
      .toLowerCase();
  }

  const escapeRegExp = value => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const indexedTerms = categories
    .flatMap(category => category.terms.flatMap(item => item.aliases.map(alias => ({
      alias: normalizeComplianceText(alias),
      categoryKey: category.key,
      categoryLabel: category.label,
      pillClass: category.pillClass,
      label: item.label,
      url: item.url,
    }))))
    .sort((a, b) => b.alias.length - a.alias.length);
  const termByAlias = new Map(indexedTerms.map(item => [item.alias, item]));
  const termPattern = new RegExp(
    `\\b(${Array.from(termByAlias.keys()).map(escapeRegExp).join('|')})\\b`,
    'gi',
  );

  function tokenizeComplianceTerms(text) {
    const visibleText = String(text);
    const normalizedText = normalizeComplianceText(visibleText);
    const segments = [];
    let cursor = 0;
    let match;

    termPattern.lastIndex = 0;
    while ((match = termPattern.exec(normalizedText)) !== null) {
      const start = match.index;
      const end = start + match[0].length;
      const tag = termByAlias.get(match[0].toLowerCase());
      if (start > cursor) segments.push({ text: visibleText.slice(cursor, start) });
      segments.push({
        text: visibleText.slice(start, end),
        categoryKey: tag.categoryKey,
        categoryLabel: tag.categoryLabel,
        pillClass: tag.pillClass,
        label: tag.label,
        ...(tag.url ? { url: tag.url } : {}),
      });
      cursor = end;
    }
    if (cursor < visibleText.length) segments.push({ text: visibleText.slice(cursor) });
    return segments;
  }

  window.GRCInsightTags = {
    categories,
    normalizeComplianceText,
    tokenizeComplianceTerms,
  };
})();
