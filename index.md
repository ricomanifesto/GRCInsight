# GRC Intelligence Report

During the period under review, GRC attention is dominated by a surge in cyber-crime enforcement actions, new compliance guidance from the FBI’s CJIS program, and a steady stream of critical software and hardware vulnerabilities that materially expand enterprise risk.  Law-enforcement agencies in the United Kingdom, United States, and France executed high-profile arrests linked to ransomware and large-scale retail breaches, underscoring increasing governmental intolerance for cyber-extortion.  On the compliance front, the FBI reiterated strict password, multi-factor authentication (MFA), and access-control expectations for any organisation handling Criminal Justice Information (CJI).  Meanwhile, technology vendors released (or were forced to release) significant security changes—including Microsoft’s move to the JScript9Legacy engine in Windows 11 and a full migration of Microsoft Authenticator iOS backups to iCloud—that alter control baselines organisations must maintain.  Persistent disclosure of exploitable defects in AI integration frameworks (Model Context Protocol), cloud platforms (ServiceNow), automotive Bluetooth stacks, chipsets (AMD), and container tooling (NVIDIA) continues to elevate supply-chain and third-party risk, demanding rapid patching, enhanced vendor management, and stronger board-level oversight of emerging technology adoption.

## Regulatory Updates and Changes

### FBI Criminal Justice Information Services (CJIS) Security Policy Guidance
- **Description**: Updated guidance emphasises stronger password hygiene, mandatory MFA, granular access control, and continuous audit logging for all entities processing Criminal Justice Information.  
- **Impact**: Law-enforcement agencies, contractors, and any service provider touching CJI must validate and document alignment with the CJIS Security Policy; gaps in MFA deployment and password complexity must be closed.  
- **Timeline**: Guidance is current and immediately enforceable; no grace period was referenced.  
- **Affected Industries**: Federal, state, and local law-enforcement agencies; justice-sector service providers; cloud/SaaS hosting CJI.  
- **Regulatory Body**: Federal Bureau of Investigation – CJIS Division  

### UK National Crime Agency (NCA) Cyber-crime Enforcement Actions
- **Description**: The NCA arrested four individuals tied to retail hacks (Marks & Spencer, Co-op, Harrods) and four alleged members of the “Scattered Spider” ransomware collective, signalling active enforcement of existing cyber-crime statutes.  
- **Impact**: Organisations should reassess incident-response readiness and cooperation protocols with UK law-enforcement; boards should anticipate more aggressive subpoenas and evidence-preservation requests.  
- **Timeline**: Arrests completed; ongoing prosecutions expected.  
- **Affected Industries**: Retail, aviation, technology, and any UK-based or UK-serving enterprise.  
- **Regulatory Body**: UK National Crime Agency (NCA)  

### U.S. Extradition & Arrest for Ransomware Negotiation
- **Description**: French authorities, acting on a U.S. request, detained a Russian professional basketball player alleged to be a ransomware negotiator, reflecting cross-border cooperation on ransomware enforcement.  
- **Impact**: Highlights legal exposure for individuals facilitating ransomware payments; companies should verify that consultants, brokers, and negotiators adhere to U.S. sanctions and anti-money-laundering rules.  
- **Timeline**: Arrest executed; extradition pending.  
- **Affected Industries**: All sectors employing third-party ransomware negotiators.  
- **Regulatory Body**: U.S. Department of Justice in coordination with French law enforcement  

## Compliance Requirements and Obligations

- **CJIS Password & MFA Controls**  
  - **Framework/Standard**: FBI CJIS Security Policy  
  - **Implementation Details**: Enforce complex, non-reused passwords; enable MFA for all interactive logons; adopt privileged-session monitoring.  

- **Microsoft Authenticator iOS Cloud Backup Change**  
  - **Framework/Standard**: Vendor security baseline / Mobile Application Management (MAM) policies  
  - **Implementation Details**: Update mobile-device-management profiles to permit or restrict iCloud storage; review data-residency and encryption requirements.  

- **Windows 11 JScript9Legacy Engine Adoption**  
  - **Framework/Standard**: Microsoft Secure Configuration Baseline  
  - **Implementation Details**: Validate application compatibility; adjust Group Policy or Intune settings to enforce updated scripting engine across fleets.  

- **Passkey (FIDO) Deployment for Passwordless Access**  
  - **Framework/Standard**: FIDO2 / WebAuthn best practices  
  - **Implementation Details**: Enable passkeys in identity providers; update user-training material; ensure fallback authentication is MFA-compliant.  

- **ServiceNow ACL Hardening (CVE-2025-3648)**  
  - **Framework/Standard**: ISO 27001 access-control domain / SOC 2 CC6  
  - **Implementation Details**: Apply vendor patch; audit Access Control Lists (ACLs) for least-privilege; monitor for unusual data export activity.  

## Risk Management Developments

- **Software Supply-Chain Vulnerabilities**  
  - **Assessment Methods**: Continuous SBOM analysis; CVE monitoring; vendor risk questionnaires.  
  - **Mitigation Strategies**: Rapid patching of MCP, mcp-remote, NVIDIA Container Toolkit, ServiceNow, AMD chipsets; implement runtime application self-protection (RASP).  

- **Ransomware & Extortion**  
  - **Assessment Methods**: Table-top exercises; backup recoverability testing; ransomware readiness assessments.  
  - **Mitigation Strategies**: Network segmentation, immutable backups, use of EDR tools, adherence to sanctions screening before any negotiations.  

- **AI Integration & Model Governance Risks**  
  - **Assessment Methods**: AI risk registers; model threat-modeling; data-flow mapping.  
  - **Mitigation Strategies**: Establish AI governance committees; require security reviews of MCP components; enforce human-in-the-loop controls.  

- **Credential Theft & SIM-Swap Fraud**  
  - **Assessment Methods**: User-behavior analytics; telecom-provider risk scoring.  
  - **Mitigation Strategies**: Phone-number change detection, hardware security keys, carrier-level port-out freezes.  

- **Automotive Bluetooth Exploits (PerfektBlue)**  
  - **Assessment Methods**: Pen-testing of in-vehicle infotainment; firmware-version tracking.  
  - **Mitigation Strategies**: Over-the-air patch deployment, isolation of critical driving systems from infotainment modules.  

## Governance and Oversight Changes

- **AI Governance for SaaS Adoption**  
  - **Requirements**: Document data-usage policies, IP ownership, and liability clauses when onboarding AI-enabled SaaS.  
  - **Accountability**: CIO/CISO jointly with a designated AI Governance Board.  

- **Board-Level Cyber-Crime Response Oversight**  
  - **Requirements**: Boards must verify existence of ransomware playbooks and law-enforcement liaison processes in light of heightened arrest activity.  
  - **Accountability**: Board Risk Committee; CFO for financial-impact analysis.  

- **Patch & Configuration Management Governance**  
  - **Requirements**: CEOs/CISOs should receive quarterly assurance that critical vendor updates (Windows JScript engine, WSUS sync fixes, AMD CPU microcode) are deployed.  
  - **Accountability**: IT Operations & Internal Audit.  

## Industry-Specific Impacts

- **Retail**  
  - **Sector-Specific Requirements**: Enhance point-of-sale segmentation; share indicators of compromise (IOCs) with the NCA-led Retail Cyber Intelligence Sharing forums.  

- **Aviation**  
  - **Sector-Specific Requirements**: Post-breach, airlines like Qantas must strengthen identity verification for loyalty programs and review data-retention schedules.  

- **Automotive Manufacturing & OEMs**  
  - **Sector-Specific Requirements**: Rapidly integrate PerfektBlue patches into dealership service workflows; validate homologation compliance for updated firmware.  

- **Cryptocurrency & Fintech**  
  - **Sector-Specific Requirements**: Bitcoin Depot breach highlights the need for end-to-end encryption of customer PII and alignment with virtual-asset service-provider (VASP) guidelines.  

- **Public Safety & Law-Enforcement IT**  
  - **Sector-Specific Requirements**: Immediate compliance with CJIS password, MFA, and logging directives; yearly policy attestations.  

- **Cloud/SaaS Providers**  
  - **Sector-Specific Requirements**: Remediate ServiceNow CVE-2025-3648, monitor for tenant-to-tenant data leakage, and provide customers with updated SOC 2 reports.  

- **Automated AI Workflows & LLM Tooling Vendors**  
  - **Sector-Specific Requirements**: Security testing of Model Context Protocol integrations and publication of vulnerability-disclosure policies.  

---

This report encapsulates the material governance, risk, and compliance developments surfaced in the referenced articles and provides actionable insights for stakeholders charged with enterprise-wide GRC oversight.