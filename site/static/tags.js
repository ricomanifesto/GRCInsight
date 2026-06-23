(function () {
  const categories = [
    {
      key: 'frameworks',
      label: 'Frameworks',
      pillClass: 'framework',
      terms: ['ISO 27001', 'ISO/IEC 27001', 'NIST', 'NIST CSF', 'COBIT', 'COSO', 'PCI-DSS'],
    },
    {
      key: 'regulations',
      label: 'Regulations',
      pillClass: 'regulation',
      terms: ['GDPR', 'CCPA', 'SOX', 'HIPAA', 'FFIEC'],
    },
    {
      key: 'risks',
      label: 'Risks',
      pillClass: 'risk',
      terms: ['Ransomware', 'Extortion', 'Third-party', 'Identity', 'Cloud misconfiguration', 'BEC'],
    },
  ];

  window.GRCInsightTags = {
    categories,
  };
})();
