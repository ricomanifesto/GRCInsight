# GRC Intelligence Report

Over the last week, cyber-threat activity has intensified around unpatched zero-day vulnerabilities (Microsoft SharePoint CVE-2025-53770, CrushFTP CVE-2025-54309) and insecure device configurations (HPE Aruba Instant On hard-coded credentials). Simultaneously, multiple software-supply-chain compromises (malicious npm and AUR packages) and sophisticated phishing techniques (PoisonSeed’s FIDO2 downgrade) illustrate a continued shift toward attacks that bypass traditional perimeter defenses. National authorities such as the UK NCSC have issued new advisories linking state-sponsored groups to credential-stealing malware, underscoring geopolitical risk. Collectively, these developments heighten regulatory expectations for timely vulnerability management, stricter third-party software governance, and enhanced identity-security controls across industries that rely on Microsoft 365, Web3, open-source ecosystems, or IoT/OT networking equipment.

## Regulatory Updates and Changes

### Microsoft Security Advisory – CVE-2025-53770 (SharePoint Server)
- **Description**: Critical remote-code-execution (RCE) zero-day in Microsoft SharePoint Server actively exploited since 18 July; no official patch yet, but Microsoft released mitigation guidance.  
- **Impact**: Organizations must apply the prescribed URL-rewrite rules, restrict external access, and enhance logging to detect exploitation.  
- **Timeline**: Active exploitation confirmed; mitigation guidance effective immediately; patch release date pending.  
- **Affected Industries**: All sectors using on-premises SharePoint (notably healthcare, finance, government, education).  
- **Regulatory Body**: Microsoft Security Response Center (MSRC).

### CrushFTP Security Bulletin – CVE-2025-54309
- **Description**: CVSS 9.0 flaw allows unauthenticated administrative access via web interface; under active exploitation.  
- **Impact**: Immediate upgrade to the fixed CrushFTP version and review of server logs for compromise indicators.  
- **Timeline**: Vulnerability disclosed and exploitation reported this week; patched versions already available.  
- **Affected Industries**: Managed-file-transfer services, media, legal, manufacturing, and any firm exchanging sensitive data via CrushFTP.  
- **Regulatory Body**: CrushFTP vendor advisory.

### HPE Aruba Instant On Security Bulletin
- **Description**: Hard-coded root credentials in specific Aruba Instant On Access Points enable authentication bypass.  
- **Impact**: Firmware update required; disable remote administration until patched; rotate all device credentials.  
- **Timeline**: Advisory released this week; firmware fix available for download.  
- **Affected Industries**: Retail, hospitality, SMBs, and enterprises using Aruba Instant On Wi-Fi infrastructure.  
- **Regulatory Body**: Hewlett Packard Enterprise (HPE) PSIRT.

### UK NCSC & Cabinet Office Advisory – “Authentic Antics” (APT28)
- **Description**: Formal attribution of Microsoft 365 credential-stealing malware “Authentic Antics” to Russia’s GRU (APT28). Guidance issued for hardening cloud identity configurations.  
- **Impact**: Public-sector and critical-infrastructure organizations must review conditional-access policies, enable MFA, and apply Microsoft cloud hardening recommendations.  
- **Timeline**: Advisory published this week with immediate actions recommended.  
- **Affected Industries**: Government, defense contractors, energy, telecoms, and any UK organization leveraging Microsoft 365.  
- **Regulatory Body**: UK National Cyber Security Centre (NCSC).

### Arch Linux Security Notice
- **Description**: Three malicious AUR packages installing Chaos RAT removed from repository.  
- **Impact**: Users must audit systems for package remnants, remove implants, and verify checksums before future AUR installs.  
- **Timeline**: Packages pulled immediately after discovery.  
- **Affected Industries**: Technology, research, and developers using Arch Linux in production or CI/CD pipelines.  
- **Regulatory Body**: Arch Linux Security Team.

## Compliance Requirements and Obligations
- **SharePoint Zero-Day Mitigation**  
  - **Framework/Standard**: CIS Benchmarks / ISO 27001 (control A.12.6.1 – technical vulnerability management)  
  - **Implementation Details**: Apply Microsoft’s URL-rewrite rules, monitor indicators of compromise (IoCs), and document compensating controls until official patching.

- **CrushFTP Patch Deployment**  
  - **Framework/Standard**: NIST SP 800-53 rev. 5 (SI-2, SI-4)  
  - **Implementation Details**: Upgrade to patched version, enable least-privilege admin accounts, and conduct post-patch penetration testing.

- **Aruba Firmware & Credential Rotation**  
  - **Framework/Standard**: PCI-DSS v4 (2.3.1 – strong authentication for system components)  
  - **Implementation Details**: Install new firmware, disable default accounts, enforce unique passwords, and document changes in configuration-management database.

- **Supply-Chain Integrity for npm/AUR**  
  - **Framework/Standard**: NIST SSDF / SOC 2 (change-management criteria)  
  - **Implementation Details**: Implement package-signing verification, use dependency-pinning, mandate SBOM generation, and conduct developer-token hygiene training.

- **Enhanced Identity Controls Against PoisonSeed**  
  - **Framework/Standard**: ISO/IEC 27001 Annex A.9 (access control)  
  - **Implementation Details**: Configure FIDO2 with strict origin checks, disable cross-device sign-in where unnecessary, and educate users on QR-based phishing.

- **Incident Reporting for State-Sponsored Threat Activity**  
  - **Framework/Standard**: GDPR/UK Data Protection Act breach-notification articles (where personal data involved)  
  - **Implementation Details**: Update incident-response playbooks to include NCSC reporting channels and 72-hour notification timelines.

## Risk Management Developments
- **Risk Area**: Zero-Day Vulnerability Exposure (SharePoint & CrushFTP)  
  - **Assessment Methods**: Real-time vulnerability scanning, CVSS prioritization, external attack-surface mapping.  
  - **Mitigation Strategies**: Rapid virtual-patch deployment, network segmentation, immutable backups.

- **Risk Area**: Software Supply-Chain Compromise (npm, AUR)  
  - **Assessment Methods**: Dependency-graph mapping, SBOM analysis, integrity monitoring.  
  - **Mitigation Strategies**: Least-privileged CI/CD service accounts, compulsory code-signing, periodic package provenance reviews.

- **Risk Area**: Identity & MFA Bypass (PoisonSeed, Authentic Antics)  
  - **Assessment Methods**: Credential-phishing simulations, audit of conditional-access logs, behavioral analytics for session hijacking.  
  - **Mitigation Strategies**: Enforce phishing-resistant MFA, disable legacy authentication, deploy risk-adaptive access controls.

- **Risk Area**: Embedded & IoT Device Weak Credentials (Aruba Instant On)  
  - **Assessment Methods**: Credential-stuffing testing, firmware-version inventory.  
  - **Mitigation Strategies**: Centralized credential vaulting, auto-update policies, network-access control (NAC) for devices.

- **Risk Area**: Geopolitical APT Activity (GRU/APT28)  
  - **Assessment Methods**: Threat-intelligence correlation, sector-specific attack surface review.  
  - **Mitigation Strategies**: Implement government-issued IoCs, participate in information-sharing programs, tabletop exercises for nation-state scenarios.

## Governance and Oversight Changes
- **Board Cyber-Risk Oversight**  
  - **Requirements**: Boards should receive briefings on zero-day exploitation windows and approve accelerated patch-management budgets.  
  - **Accountability**: CISO must present weekly status until SharePoint and CrushFTP patches fully deployed.

- **Third-Party Software Governance**  
  - **Requirements**: Establish formal approval workflow for all open-source packages and mandate SBOM inclusion in vendor contracts.  
  - **Accountability**: CTO supported by Procurement & Internal Audit.

- **Identity & Access Governance**  
  - **Requirements**: Quarterly review of MFA effectiveness and policy exceptions in light of PoisonSeed attack path.  
  - **Accountability**: IAM Program Manager reports to CIO and Audit Committee.

- **Incident-Response Governance**  
  - **Requirements**: Update playbooks to align with NCSC advisory requirements and specify roles for regulatory notifications.  
  - **Accountability**: Head of Security Operations Center (SOC).

## Industry-Specific Impacts

- **Financial Services**  
  - **Impacts**: Heightened regulatory scrutiny on exploit window for SharePoint servers used in client-data portals.  
  - **Sector-Specific Requirements**: Immediate reporting to regulators if material impact on customer data (per FCA, FDIC guidance).

- **Healthcare & Life Sciences**  
  - **Impacts**: Potential HIPAA exposure if PHI stored on unpatched SharePoint or transferred via CrushFTP.  
  - **Sector-Specific Requirements**: Conduct HIPAA Security Rule risk assessment focusing on these systems.

- **Technology & Software Development (Web3 / npm)**  
  - **Impacts**: Supply-chain attacks threaten integrity of decentralized-app codebases.  
  - **Sector-Specific Requirements**: Implement continuous dependency scanning; maintain signed commit policies for smart-contract repositories.

- **Retail & Hospitality (Aruba Instant On)**  
  - **Impacts**: Compromised Wi-Fi infrastructure could expose POS traffic and guest data.  
  - **Sector-Specific Requirements**: Align firmware updates with PCI-DSS compliance schedule; perform quarterly wireless penetration tests.

- **Government & Defense Contractors**  
  - **Impacts**: GRU-linked malware elevates requirement for strengthened cloud-identity governance.  
  - **Sector-Specific Requirements**: Follow UK NCSC advisory controls; map compliance to NIST 800-171 or government accreditation regimes.