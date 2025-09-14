# GRC Intelligence Report

A series of government advisories, security bulletins, and enforcement actions emerged this week that materially affect governance, risk, and compliance programs.  Highlights include a U.S. FBI flash alert on two threat groups actively exfiltrating data from Salesforce tenants, a CISA warning about active exploitation of a critical Dassault DELMIA Apriso flaw in manufacturing environments, and a Samsung patch for a zero-day (CVE-2025-21043) abused in Android attacks.  The FTC has opened an investigation into seven large AI-companion providers over child-safety concerns, while CERT-FR issued twin advisories on spyware targeting Apple devices in France.  Microsoft reminded customers that Windows 11 23H2 reaches end-of-support in 60 days, imposing an urgent upgrade requirement.  Additional risk notices cover a Cursor terminal vulnerability, a new HybridPetya ransomware strain that bypasses UEFI Secure Boot, and undocumented radios discovered in solar-powered highway devices.  Collectively, these updates require immediate board-level visibility, accelerated patch management, and enhanced third-party and product governance.

---

## Regulatory Updates and Changes

### FBI Flash Alert – UNC6040 & UNC6395 Targeting Salesforce
- **Description**: The FBI released indicators of compromise (IoCs) linked to two cyber-criminal groups conducting credential-stuffing and session-hijacking attacks to steal data from Salesforce platforms.
- **Impact**: Organizations must ingest the IoCs, harden Salesforce authentication (MFA, IP allow-lists), review audit logs, and disable unused API tokens.
- **Timeline**: Alert issued early September 2025; mitigation recommended immediately.
- **Affected Industries**: Any sector running Salesforce, especially retail, healthcare, and financial services with large customer datasets.
- **Regulatory Body**: U.S. Federal Bureau of Investigation (FBI).

### CISA Advisory – Critical DELMIA Apriso RCE Exploitation
- **Description**: CISA warned that attackers are actively exploiting a critical remote-code-execution vulnerability in Dassault’s DELMIA Apriso manufacturing-operations-management software.
- **Impact**: Patch DELMIA Apriso to the vendor-recommended version, isolate the MOM environment, and monitor for anomalous outbound traffic.
- **Timeline**: Advisory released in early September 2025; patch immediately.
- **Affected Industries**: Manufacturing, automotive, aerospace, and any plant using DELMIA Apriso.
- **Regulatory Body**: Cybersecurity and Infrastructure Security Agency (CISA).

### FTC Investigation – AI Companion Safety for Minors
- **Description**: The FTC is scrutinizing OpenAI, Meta, and five other firms over reports that AI companions provide inappropriate content to children and insufficient parental controls.
- **Impact**: Firms must preserve documents, perform internal risk assessments, and demonstrate compliance with child-safety and privacy obligations.
- **Timeline**: Investigations announced September 2025; response deadlines specified in agency subpoenas.
- **Affected Industries**: AI chatbot providers, social-media platforms, and ed-tech firms.
- **Regulatory Body**: Federal Trade Commission (FTC).

### CERT-FR Advisory – Apple Spyware Activity
- **Description**: CERT-FR published guidance after Apple disclosed a zero-day used in “sophisticated attacks” and sent threat notifications to French users—the fourth campaign this year.
- **Impact**: Update iOS/macOS devices to Apple’s latest security releases, enable Lockdown Mode for high-risk users, and follow CERT-FR hardening steps.
- **Timeline**: Advisory issued one week after Apple notifications in September 2025.
- **Affected Industries**: Journalists, dissidents, high-net-worth individuals, and enterprises with Apple fleets in France.
- **Regulatory Body**: Computer Emergency Response Team – France (CERT-FR).

### Windows 11 23H2 End-of-Support Notice
- **Description**: Microsoft reminded customers that Windows 11 Home and Pro edition 23H2 will stop receiving security updates in roughly 60 days.
- **Impact**: Upgrade to a supported release (e.g., 24H2) or risk operating unsupported systems, which can violate internal security policies and third-party audit requirements.
- **Timeline**: Support ends in November 2025.
- **Affected Industries**: All sectors running Windows endpoints.
- **Regulatory Body**: Microsoft product lifecycle authority (vendor-set obligation).

### Samsung Security Bulletin – CVE-2025-21043 Zero-Day
- **Description**: Samsung’s monthly Android bulletin fixed CVE-2025-21043, a vulnerability actively exploited in the wild.
- **Impact**: Mobile-fleet administrators must deploy the September 2025 security patch to Samsung devices and update MDM compliance rules.
- **Timeline**: Patch released September 2025; apply immediately.
- **Affected Industries**: Enterprises with corporate or BYOD Samsung Android devices.
- **Regulatory Body**: Vendor security advisory (Samsung).

### USDOT Alert – Undocumented Radios in Solar-Powered Highway Devices
- **Description**: The U.S. Transportation Department warned that certain solar-powered infrastructure devices contain undocumented radios that could be remotely accessed.
- **Impact**: State and local transportation agencies must inventory affected devices, disable undocumented radios, and review vendor supply-chain assurances.
- **Timeline**: Warning circulated September 2025.
- **Affected Industries**: Transportation, smart-city, and critical-infrastructure operators.
- **Regulatory Body**: U.S. Department of Transportation (USDOT).

---

## Compliance Requirements and Obligations
- **Salesforce IOC Monitoring**
  - Framework/Standard: Incident-response best practice
  - Implementation Details: Ingest FBI IoCs into SIEM, enable detailed login-history tracking, enforce MFA.

- **Patch DELMIA Apriso Critical RCE**
  - Framework/Standard: CISA advisory / vendor patch management
  - Implementation Details: Apply vendor hotfix, perform post-patch scans, document change-control approval.

- **Child-Safety Controls for AI Companions**
  - Framework/Standard: FTC child-protection obligations
  - Implementation Details: Implement robust age-verification, content-filtering, and audit logging; submit compliance evidence to FTC if requested.

- **iOS/macOS Emergency Security Updates**
  - Framework/Standard: CERT-FR mitigation
  - Implementation Details: Force install latest Apple security updates via MDM; enable Lockdown Mode for high-risk profiles.

- **Windows 11 Lifecycle Management**
  - Framework/Standard: Microsoft product-support policy
  - Implementation Details: Upgrade devices to 24H2 or later; validate application compatibility; update asset inventory.

- **Samsung Mobile Security Patch Deployment**
  - Framework/Standard: Vendor security bulletin
  - Implementation Details: Push September 2025 patch via EMM; block devices on older patch levels.

- **Cursor Terminal Hardening**
  - Framework/Standard: Secure-configuration management
  - Implementation Details: Disable the vulnerable feature that auto-executes commands; deploy patched version when released.

- **UEFI Secure-Boot Validation**
  - Framework/Standard: Endpoint-protection baseline
  - Implementation Details: Verify UEFI Secure Boot configuration; deploy firmware updates that block HybridPetya bypass vector.

- **VPN App Due-Diligence**
  - Framework/Standard: Third-party risk management
  - Implementation Details: Review privacy policies, perform penetration tests, and restrict high-risk free VPN applications.

---

## Risk Management Developments

- **Data-Exfiltration via SaaS Platforms**
  - Assessment Methods: Monitor API usage, review anomaly-detection alerts, validate MFA enrollment.
  - Mitigation Strategies: Enforce least-privilege roles, rotate credentials, and implement CASB controls.

- **Critical Software Vulnerabilities (DELMIA Apriso, Samsung Android, Cursor)**
  - Assessment Methods: External vulnerability scanning, SBOM review.
  - Mitigation Strategies: Accelerated patch cycles, compensating network segmentation, and vendor-risk scorecards.

- **Ransomware Evolution – HybridPetya UEFI Bypass**
  - Assessment Methods: Firmware integrity checks, boot-kit detection tools.
  - Mitigation Strategies: Enable Secure Boot, deploy endpoint detection and response (EDR) with firmware-level telemetry, maintain tested offline backups.

- **Spyware Campaigns Targeting Apple Devices**
  - Assessment Methods: Mobile threat-defense analytics, alert correlation with Apple threat notifications.
  - Mitigation Strategies: Immediate OS updates, Lockdown Mode, user-awareness training.

- **AI Companion Misuse & Child Safety**
  - Assessment Methods: Content safety audits, red-team simulations with youth-oriented prompts.
  - Mitigation Strategies: Age-gating, parental-control dashboards, ethical-AI review boards.

- **Undocumented Radios in OT / IoT Devices**
  - Assessment Methods: RF spectrum analysis, hardware bill-of-materials (HBOM) inspections.
  - Mitigation Strategies: Disable or physically remove undocumented radios, deploy tamper-detection seals.

- **Unsupported Operating Systems (Windows 11 23H2)**
  - Assessment Methods: Asset inventory with lifecycle flags.
  - Mitigation Strategies: Upgrade planning, virtual patching, extended-support contracts where upgrading is delayed.

---

## Governance and Oversight Changes

- **AI Product Governance**
  - Requirements: Establish a child-safety committee reporting to the board; integrate ethical-AI checkpoints in SDLC.
  - Accountability: Chief Product Officer and Chief Compliance Officer jointly own oversight.

- **Vulnerability & Patch Governance**
  - Requirements: 14-day SLA for critical vendor patches (Samsung, Dassault, Apple); quarterly board reporting on patch compliance.
  - Accountability: CISO and IT Operations.

- **Third-Party SaaS Oversight**
  - Requirements: Annual security-review of core SaaS (e.g., Salesforce), including credential-stuffing resilience testing.
  - Accountability: Vendor-Risk Management Committee.

- **Lifecycle Management Governance**
  - Requirements: Policy mandating that no endpoints operate beyond vendor support dates.
  - Accountability: CIO and Internal Audit.

- **OT/ICS Security Governance**
  - Requirements: Risk ownership for undocumented radios and similar supply-chain issues placed under the Enterprise Risk Management (ERM) function.
  - Accountability: VP of Operations Technology.

---

## Industry-Specific Impacts

- **Manufacturing & Industrial**
  - Sector-Specific Requirements: Patch DELMIA Apriso immediately; review OT network segmentation due to HybridPetya UEFI risk.

- **Technology & SaaS Providers**
  - Sector-Specific Requirements: Integrate FBI IoCs into threat-hunting for Salesforce; ensure continuous monitoring of AI companion safety features.

- **Telecommunications & Mobile Operators**
  - Sector-Specific Requirements: Deploy Samsung CVE-2025-21043 patch across subscriber devices; enhance supply-chain attestation for Android firmware.

- **Financial Services & Retail**
  - Sector-Specific Requirements: Audit Salesforce data-access logs and enable token-based session timeout policies to deter credential-stuffing.

- **Transportation & Smart-City Infrastructure**
  - Sector-Specific Requirements: Inventory solar-powered highway devices for undocumented radios; update procurement policies to require component transparency.

- **Education & Child-Focused Platforms**
  - Sector-Specific Requirements: Align AI companion design with FTC child-safety expectations; document parental-consent mechanisms.

---

**End of Report**

