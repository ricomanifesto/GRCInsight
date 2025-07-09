# GRC Intelligence Report

July 2025 news highlights signal a busy governance, risk, and compliance (GRC) landscape. Regulatory authorities tightened post-breach enforcement (South Korea vs. SK Telecom), issued fresh vulnerability remediation mandates (CISA’s KEV additions), and accelerated cryptographic hygiene requirements (industry move to 47-day SSL/TLS certificates by 2029). Vendors released large volumes of security patches—Microsoft alone addressed 130-137 CVEs across two Patch Tuesday drops—driving new compliance obligations for timely patch management. Emerging authentication methods (passkeys) and extended Windows 10 security-update options reshape control frameworks for identity and end-of-life software. Threat intelligence underscores heightened risks from software-supply-chain attacks (188 % YoY rise in malicious open-source packages, VS Code–Ethcode compromise), mobile malware (Anatsa, TapTrap), and data-stealing Chrome extensions. Boards are expected to strengthen oversight of vulnerability management, third-party risk, and privacy controls amid expanding sector-specific threats to telecom, retail, and financial services.

---

## Regulatory Updates and Changes

### South Korean Government Post-Breach Enforcement against SK Telecom
- **Description**: Regulators imposed a monetary penalty and mandated corrective actions after a breach exposed 27 million customer records.
- **Impact**: SK Telecom must implement stronger technical safeguards, increase breach-notification transparency, and submit regular security-audit reports.
- **Timeline**: Immediate penalty; ongoing reporting cadence not specified in article.
- **Affected Industries**: Telecommunications and critical infrastructure operators in South Korea.
- **Regulatory Body**: Ministry of Science and ICT / Korea Communications Commission.

### CISA Known Exploited Vulnerabilities (KEV) Catalog Additions
- **Description**: Four actively exploited CVEs were added to CISA’s KEV catalog, signalling mandatory remediation for federal agencies and strong guidance for the private sector.
- **Impact**: Entities following U.S. federal guidance must identify affected systems and apply patches or mitigations within the agency-defined timeframe.
- **Timeline**: Specific remediation deadlines were not stated in the article.
- **Affected Industries**: All U.S. federal civilian agencies; recommended for critical infrastructure and private enterprises.
- **Regulatory Body**: U.S. Cybersecurity and Infrastructure Security Agency (CISA).

### Shortened SSL/TLS Certificate Lifespan Policy (47-Day Certificates)
- **Description**: Industry stakeholders agreed to reduce certificate validity periods to 47 days by 2029 to improve cryptographic agility.
- **Impact**: Organizations must overhaul certificate lifecycle management processes, automate renewals, and update inventory systems to avoid service outages.
- **Timeline**: Transition period culminating in 2029; preparatory planning recommended within the next 100 days.
- **Affected Industries**: All sectors using public-trust SSL/TLS certificates.
- **Regulatory Body**: Industry governance via Certificate Authority/Browser (CA/B) Forum (not a government agency).

### Microsoft Windows 10 Extended Security Updates (ESU) Options
- **Description**: Microsoft offered two no-cost avenues (Windows 365 Cloud PCs and Azure Virtual Desktop) to receive security updates through October 2026, supplementing the paid ESU program.
- **Impact**: Organizations relying on Windows 10 must choose an ESU path or migrate to supported OS versions to maintain compliance with security-patch requirements.
- **Timeline**: Free update paths are available immediately; official Windows 10 end of support remains October 14 2025, with ESU coverage until October 2026.
- **Affected Industries**: All sectors with Windows 10 deployments, notably healthcare, finance, and government.
- **Regulatory Body**: Vendor policy (Microsoft) influencing compliance with industry cybersecurity regulations.

---

## Compliance Requirements and Obligations

- **Timely Patch Management**
  - **Framework/Standard**: ISO 27001 A.12.6; NIST CSF PR.IP-12
  - **Implementation Details**: Apply July 2025 Microsoft patches (130–137 CVEs) across Windows, Office, SQL Server, SharePoint, and SPNEGO components; document testing and deployment.

- **Breach-Response Reporting (SK Telecom Case)**
  - **Framework/Standard**: South Korea’s Personal Information Protection Act (PIPA)
  - **Implementation Details**: Enhance incident-response plans, ensure 24-hour supervisory-authority notification, and schedule periodic third-party audits.

- **Certificate Lifecycle Automation**
  - **Framework/Standard**: CA/B Forum Baseline Requirements
  - **Implementation Details**: Deploy automated renewal pipelines, maintain real-time certificate inventories, and integrate expiration alerts to meet future 47-day validity limits.

- **End-of-Life Software Governance**
  - **Framework/Standard**: CIS Controls 2 & 7; PCI-DSS 4.0 clause 6.3.3 (supported software)
  - **Implementation Details**: Enroll Windows 10 assets in Microsoft’s ESU program or migrate to Windows 11; update asset registers and risk assessments.

- **Passwordless Authentication Adoption**
  - **Framework/Standard**: FIDO2 / WebAuthn
  - **Implementation Details**: Roll out passkeys for workforce and customer access, update access-control policies, and enable phishing-resistant MFA tracking.

- **Third-Party Extension Security**
  - **Framework/Standard**: NIST SP 800-218 (Secure Software Development Framework)
  - **Implementation Details**: Conduct SBOM reviews on VS Code and browser extensions; enforce approval workflows for open-source packages and Chrome Web Store add-ons.

---

## Risk Management Developments

- **Software Supply-Chain Risk**
  - **Assessment Methods**: Continuous monitoring of public repositories; SBOM analysis; threat-intel feeds (Sonatype report shows 188 % YoY spike).
  - **Mitigation Strategies**: Implement dependency pinning, sandbox build environments, and automatic vulnerability scanning for open-source components.

- **Mobile Malware & Tapjacking**
  - **Risk Area**: Android ecosystem (Anatsa banking trojan, TapTrap technique).
  - **Assessment Methods**: Mobile Threat Defense (MTD) telemetry; behavioral analytics on app permissions.
  - **Mitigation Strategies**: Enforce enterprise app-store whitelists, enable Google Play Protect reporting, mandate least-privilege permission policies.

- **Credential & Identity Attacks**
  - **Risk Area**: Retail sector (identity-based breaches, M&S ransomware).
  - **Assessment Methods**: Privileged-access reviews; social-engineering simulations.
  - **Mitigation Strategies**: Privileged Access Management (PAM), just-in-time access, enhanced employee phishing training.

- **IoT & DDoS Botnets**
  - **Risk Area**: RondoDox exploiting DVRs and routers.
  - **Assessment Methods**: Network segmentation audits; device firmware posture scanning.
  - **Mitigation Strategies**: Enforce default-password changes, apply vendor firmware updates, isolate DVR/IoT devices from critical networks.

- **Browser Extension Threats**
  - **Risk Area**: Malicious Chrome add-ons with 1.7 M installs.
  - **Assessment Methods**: Browser management policies; extension reputation scoring.
  - **Mitigation Strategies**: Centralized allow-list configuration, periodic extension audits, and user awareness campaigns.

---

## Governance and Oversight Changes

- **Post-Incident Regulatory Oversight (Telecom)**
  - **Requirements**: Board-level security committee must certify compliance with new South Korean mandates and oversee remediation funding.
  - **Accountability**: CISO and Risk Committee report quarterly to regulators.

- **Certificate Governance**
  - **Requirements**: Establish executive-approved PKI governance charters to address 47-day certificate rotations.
  - **Accountability**: CIO/CTO responsible for automation investment; Internal Audit to test controls pre-2029.

- **Vulnerability Management Visibility**
  - **Governance Area**: Board reporting on critical CVE backlogs (prompted by consecutive Microsoft mega-patch cycles).
  - **Requirements**: Monthly KPI/KRI dashboards on patch latency and KEV alignment.
  - **Accountability**: Enterprise Risk Management (ERM) function and IT Operations.

- **Software-Supply-Chain Oversight**
  - **Governance Area**: Third-party risk and DevSecOps.
  - **Requirements**: Adopt policy requiring SBOM attestation from vendors and internal development teams.
  - **Accountability**: Chief Procurement Officer and VP of Engineering.

---

## Industry-Specific Impacts

- **Telecommunications**
  - **Impacts**: Mandatory security audits; heightened personal-data protection expectations after SK Telecom breach.
  - **Sector-Specific Requirements**: Telecom service providers must integrate continuous monitoring per Korean regulatory guidance.

- **Retail**
  - **Impacts**: Increase in social-engineering and identity-based attacks (M&S case, retail breach analysis).
  - **Sector-Specific Requirements**: Deploy adaptive fraud-detection systems and strengthen supplier-access governance.

- **Financial Services**
  - **Impacts**: Mobile banking trojans (Anatsa) and AI-driven scam interception (PayPal) heighten transaction-fraud controls.
  - **Sector-Specific Requirements**: Implement real-time behavioral analytics; reinforce customer-authentication layers.

- **Public Sector**
  - **Impacts**: CISA KEV mandates and TAG-140 targeting of Indian government agencies intensify vulnerability-management and email-security controls.
  - **Sector-Specific Requirements**: Government entities must patch KEV-listed CVEs rapidly and harden endpoint defenses.

- **Technology & Software Development**
  - **Impacts**: Malicious VS Code extension (Ethcode) and surge in compromised open-source packages require stricter developer-tool governance.
  - **Sector-Specific Requirements**: Continuous code-integrity scanning, enforce trusted-repository policies, and vet red-team tools (Shellter misuse).

---

End of Report