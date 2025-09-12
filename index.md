# GRC Intelligence Report

During the last news cycle, authorities and security researchers highlighted several material developments that affect governance, risk, and compliance programs. The U.S. Cybersecurity and Infrastructure Security Agency (CISA) added a critical Dassault DELMIA Apriso remote-code-execution flaw to its Known Exploited Vulnerabilities catalog, triggering mandatory federal patching obligations and raising the bar for supplier-risk oversight across manufacturing. The U.S. Food and Drug Administration (FDA) cleared Apple’s forthcoming Hypertension Detection feature for Apple Watch, illustrating the growing convergence of consumer wearables and regulated medical-device requirements. Microsoft reminded customers that Windows 11 23H2 Home and Pro will reach end of support in 60 days, creating an urgent lifecycle-management compliance issue. Separately, new research revealed HybridPetya ransomware’s ability to bypass UEFI Secure Boot, Samsung patched actively exploited zero-day CVE-2025-21043, and CERT-FR confirmed a fourth spyware campaign targeting French Apple users—all of which heighten enterprise threat exposure. Finally, the U.S. Transportation Department’s warning about undocumented radios in solar-powered highway devices underscores emerging operational-technology (OT) governance gaps.

## Regulatory Updates and Changes

### CISA Known Exploited Vulnerability (KEV) Catalog – Dassault DELMIA Apriso RCE
- **Description**: CISA issued an alert that attackers are actively exploiting a critical remote-code-execution vulnerability in Dassault’s DELMIA Apriso manufacturing-operations-management platform. The flaw has been added to the KEV catalog, signaling confirmed in-the-wild exploitation.  
- **Impact**: U.S. federal civilian agencies must identify and remediate the vulnerability on all affected systems. Private-sector organizations should adopt the same timeline to avoid supply-chain exposure and contractual non-compliance.  
- **Timeline**: Binding Operational Directive (BOD) timelines apply from the KEV listing date; federal agencies typically have three weeks to patch (exact deadline not specified in the article).  
- **Affected Industries**: Manufacturing, aerospace & defense, automotive, and any sector using DELMIA Apriso for MOM.  
- **Regulatory Body**: U.S. Cybersecurity and Infrastructure Security Agency (CISA).

### FDA Clearance – Apple Watch Hypertension Detection
- **Description**: The FDA granted clearance for Apple’s Hypertension Detection feature, allowing Apple Watch hardware and watchOS 26 software to provide regulated blood-pressure-related insights.  
- **Impact**: Apple and third-party health-app developers must comply with post-market surveillance, quality-system, and labeling requirements associated with FDA-cleared Class II software functions. Covered healthcare entities integrating the feature must ensure HIPAA and medical-device-integration controls are in place.  
- **Timeline**: Feature will roll out with watchOS 26 (no specific date provided).  
- **Affected Industries**: Digital health, hospitals, insurers, health-tech integrators.  
- **Regulatory Body**: U.S. Food and Drug Administration (FDA).

### End-of-Support Notice – Windows 11 23H2 Home & Pro
- **Description**: Microsoft announced that Windows 11 23H2 Home and Pro editions will stop receiving security updates in November (60 days from the notice).  
- **Impact**: Organizations must upgrade affected endpoints or risk operating unsupported software, which can breach internal security baselines, third-party contract clauses, and cyber-insurance conditions.  
- **Timeline**: November (exact day not specified) – final security updates; no further patches afterward.  
- **Affected Industries**: All sectors operating Windows endpoints.  
- **Regulatory Body**: Microsoft (vendor lifecycle policy; indirectly referenced by multiple cyber-insurance and regulatory frameworks).

### U.S. Department of Transportation (DOT) Advisory – Undocumented Radios in Solar-Powered Highway Devices
- **Description**: DOT reportedly warned that certain solar-powered infrastructure devices contain undocumented wireless radios, posing potential unauthorized-communication risks.  
- **Impact**: State and municipal transportation agencies must inventory field devices, disable or secure undocumented transceivers, and update procurement specifications.  
- **Timeline**: Advisory date not specified; agencies urged to act immediately.  
- **Affected Industries**: Transportation, energy, critical infrastructure, smart-city integrators.  
- **Regulatory Body**: U.S. Department of Transportation (DOT).

### CERT-FR Security Alert – Spyware Campaign Targeting French Apple Users
- **Description**: The French Computer Emergency Response Team (CERT-FR) confirmed Apple’s fourth 2025 notification wave warning French users of an active spyware campaign.  
- **Impact**: French organizations should verify mobile-device-management (MDM) posture, enforce iOS patch levels, and inform potentially affected executives or high-risk personnel.  
- **Timeline**: Alerts sent on 26 September 2025 (exact date provided in article).  
- **Affected Industries**: Government, critical infrastructure, media, and high-profile private enterprises in France.  
- **Regulatory Body**: CERT-FR (national cybersecurity authority).

## Compliance Requirements and Obligations

- **Federal KEV Patch Management**
  - **Framework/Standard**: CISA Binding Operational Directive 22-01
  - **Implementation Details**: Identify DELMIA Apriso instances, apply vendor patch or mitigations within the KEV-mandated window, and submit compliance attestation.

- **Medical-Device Quality System Updates for Hypertension Detection**
  - **Framework/Standard**: FDA 21 CFR 820 Quality System Regulation
  - **Implementation Details**: Update design-history files, labeling, and post-market surveillance plans for wearables incorporating the Apple feature.

- **Operating-System Lifecycle Governance**
  - **Framework/Standard**: CIS Controls v8 – Control 04 (Secure Configuration of Enterprise Assets)
  - **Implementation Details**: Create migration plans for Windows 11 23H2 devices; document residual-risk acceptance for any systems not upgraded by November.

- **OT Asset Discovery and Radio-Frequency (RF) Risk Mitigation**
  - **Framework/Standard**: NIST SP 800-82 Rev. 3 (Guide to Industrial Control Systems Security)
  - **Implementation Details**: Conduct field surveys, update asset inventory, disable undocumented radios, and revise procurement contracts.

- **Mobile Threat Defense for French Entities**
  - **Framework/Standard**: ISO/IEC 27001 Annex A.5 (Information-security policies)
  - **Implementation Details**: Enforce mobile OS patch compliance, deploy MDM geo-fencing, and educate end-users about phishing vectors tied to the spyware campaign.

## Risk Management Developments

- **Risk Area**: Firmware-Level Ransomware (HybridPetya)
  - **Assessment Methods**: Firmware-integrity scanning, Secure-Boot validation audits.
  - **Mitigation Strategies**: Apply motherboard firmware updates, enable hardware-root-of-trust features, and maintain tested offline backups.

- **Risk Area**: Android Zero-Day Exploits (CVE-2025-21043)
  - **Assessment Methods**: Mobile-device-security monitoring for abnormal privilege escalation.
  - **Mitigation Strategies**: Deploy Samsung’s September security patch, enforce device-encryption policies.

- **Risk Area**: Untrusted VPN Providers
  - **Assessment Methods**: Supply-chain due-diligence reviews, code-audit requirements, and ownership-structure checks.
  - **Mitigation Strategies**: Prefer audited, RAM-only VPN infrastructures; require no-log attestations.

- **Risk Area**: Unsupported Operating Systems
  - **Assessment Methods**: Endpoint-management reports on OS version coverage.
  - **Mitigation Strategies**: Accelerate OS upgrades, implement network isolation for legacy assets.

- **Risk Area**: OT Wireless Exposure
  - **Assessment Methods**: RF-spectrum analysis and penetration testing of solar-powered field devices.
  - **Mitigation Strategies**: Disable undocumented radios, implement whitelisting of allowed frequencies, and monitor telemetry.

- **Risk Area**: Intellectual-Property Theft (Unreleased Movies Case)
  - **Assessment Methods**: Insider-threat analytics, physical-access controls review.
  - **Mitigation Strategies**: Strengthen employee vetting, introduce watermarking, and log monitoring of high-value content access.

## Governance and Oversight Changes

- **Shared Cyber-Defense Responsibility**
  - **Requirements**: The “Without Federal Help” op-ed urges boards and executives to incorporate collective-defense principles into governance charters.
  - **Accountability**: CISOs to present community-engagement metrics and joint-threat-intel participation to audit committees.

- **Incident-Response Preparedness**
  - **Requirements**: “First Three Things You’ll Want During a Cyberattack” article highlights clarity, control, and recovery as board-reportable KPIs.
  - **Accountability**: Incident-response (IR) leaders must maintain current playbooks and quarterly tabletop exercises.

- **VPN Data-Privacy Oversight**
  - **Requirements**: Boards should demand independent security-audit reports before approving consumer or employee VPN procurement.
  - **Accountability**: Procurement and Data-Privacy Officers jointly responsible.

- **Product-Lifecycle Governance**
  - **Requirements**: CIOs must brief audit committees on the Windows 11 end-of-support schedule and obtain budget approval for migration.
  - **Accountability**: IT asset-management teams to report progress monthly.

## Industry-Specific Impacts

- **Manufacturing**
  - **Sector-Specific Requirements**: Patch DELMIA Apriso RCE immediately; review supplier security clauses.

- **Healthcare & Digital Health**
  - **Sector-Specific Requirements**: Integrate FDA-cleared Hypertension Detection under existing medical-device risk-management processes; ensure HIPAA compliance.

- **Transportation & Critical Infrastructure**
  - **Sector-Specific Requirements**: Inventory solar-powered roadway devices; secure or remove undocumented radios per DOT advisory.

- **Mobile & Telecommunications**
  - **Sector-Specific Requirements**: Apply Samsung CVE-2025-21043 patch; deploy mobile threat-defense solutions to detect spyware campaigns.

- **Media & Entertainment**
  - **Sector-Specific Requirements**: Enhance insider-threat controls following the 57-month prison sentence for movie theft; strengthen DRM enforcement.

- **General Enterprise IT**
  - **Sector-Specific Requirements**: Plan OS migrations before Windows 11 23H2 end-of-support; update firmware-level defenses against HybridPetya.

---

This report aggregates publicly available information from the cited articles and should be integrated into existing GRC dashboards, risk registers, and compliance calendars for timely action.