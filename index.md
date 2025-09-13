# GRC Intelligence Report

Recent cybersecurity advisories and regulatory actions underscore a sharp rise in technology-driven risk, with special attention on AI tools, mobile spyware, and supply-chain software vulnerabilities.  The U.S. Federal Trade Commission (FTC) has opened a broad inquiry into the safety of AI “companion” products aimed at children, signaling potential new privacy-by-design obligations.  National computer-emergency teams (CERT-FR) and CISA have both issued urgent alerts on active exploitation of zero-day flaws in Apple devices and Dassault’s DELMIA Apriso platform, respectively, while Microsoft reminds customers that Windows 11 23H2 support ends in November, creating a looming compliance gap for un-migrated assets.  New ransomware that bypasses UEFI Secure Boot, critical flaws in the Cursor AI-coding IDE, and revelations about undocumented radios in solar-powered transportation devices highlight emerging attack surfaces that organizations must incorporate into risk assessments and board-level cyber-governance.  

## Regulatory Updates and Changes

### FTC Inquiry into AI Companion Products for Children  
- **Description**: The FTC has formally demanded information from seven technology companies (including OpenAI and Meta) regarding safeguards, data-collection practices, and content moderation controls for AI “companions” marketed to minors.  
- **Impact**: Firms offering AI chatbots or virtual companions must prepare to demonstrate child-safety controls, age-verification procedures, and COPPA-aligned data-handling practices.  Expect heightened scrutiny of algorithmic transparency and content filtering.  
- **Timeline**: Requests for information have been issued; companies must respond within the statutory period (exact dates not included in the article).  
- **Affected Industries**: Social media, EdTech, consumer AI application providers.  
- **Regulatory Body**: U.S. Federal Trade Commission (FTC).  

### CISA Adds Dassault DELMIA Apriso RCE to Known Exploited Vulnerabilities (KEV) Catalog  
- **Description**: CISA warns that threat actors are actively exploiting a critical remote-code-execution flaw in DELMIA Apriso manufacturing-operations-management software.  The vulnerability allows unauthenticated takeover of industrial environments.  
- **Impact**: Federal agencies and organizations following CISA guidance must apply the vendor patch or discontinue use until mitigated; failure to do so may trigger non-compliance with Binding Operational Directive patch-timeframes.  
- **Timeline**: Added to KEV catalog immediately; patching deadlines tied to CISA directive (specific date not provided in article).  
- **Affected Industries**: Manufacturing, industrial automation, critical infrastructure that uses Apriso platforms.  
- **Regulatory Body**: U.S. Cybersecurity and Infrastructure Security Agency (CISA).  

### Microsoft End-of-Support Notice for Windows 11 23H2 (Home & Pro)  
- **Description**: Microsoft confirms that Windows 11 23H2 Home and Pro editions will no longer receive security updates after November (60-day notice issued).  
- **Impact**: Organizations must upgrade devices or risk falling out of vendor-supported status, affecting internal policy compliance, vulnerability-management SLAs, and audit readiness.  
- **Timeline**: Support ends in November (specific day not stated).  
- **Affected Industries**: All sectors with Windows endpoints.  
- **Regulatory Body**: Microsoft (vendor lifecycle policy).  

### U.S. Department of Transportation Bulletin on Undocumented Radios in Solar-Powered Highway Devices  
- **Description**: The Transportation Department warns state authorities that certain solar-powered roadside units contain undocumented radio transceivers that could be remotely accessed.  
- **Impact**: Agencies must inventory affected hardware, disable or replace devices, and update procurement controls to ensure supply-chain transparency.  
- **Timeline**: Advisory issued (dates not listed).  
- **Affected Industries**: Transportation, state/local government, critical infrastructure operators deploying roadside IoT.  
- **Regulatory Body**: U.S. Department of Transportation.  

### CERT-FR Advisory on Repeated Apple Spyware Campaigns  
- **Description**: CERT-FR corroborates Apple’s fourth notification series to French users about sophisticated spyware exploiting an undisclosed zero-day to target high-profile individuals.  
- **Impact**: Entities handling sensitive French citizen data must update Apple devices promptly and consider mobile-threat-defense (MTD) controls to maintain GDPR security-by-design posture.  
- **Timeline**: Alerts sent 4 September; mitigation guidance issued concurrently.  
- **Affected Industries**: Government, journalism, defense, and any organization with high-risk iOS users in France.  
- **Regulatory Body**: CERT-FR (French national CSIRT).  

## Compliance Requirements and Obligations

- **Patch Samsung Android Devices (CVE-2025-21043)**  
  - Framework/Standard: Vendor security bulletin; aligns with ISO 27001 A.12.6.1 (technical vulnerability management).  
  - Implementation Details: Deploy September security update across all Samsung models listed in the advisory.  

- **Mitigate Cursor IDE Auto-Run Command Vulnerability**  
  - Framework/Standard: Secure-coding / DevSecOps best practices.  
  - Implementation Details: Disable the “Allow any command to run automatically” feature until patched; review CI/CD pipelines for malicious code-injection.  

- **Upgrade or Replace Windows 11 23H2 Home/Pro Endpoints**  
  - Framework/Standard: NIST SP 800-40 vulnerability remediation guidance.  
  - Implementation Details: Transition to a supported Windows build, or enforce compensating controls and network segmentation for legacy devices before November.  

- **Apply Dassault DELMIA Apriso Security Patch**  
  - Framework/Standard: CISA KEV compliance; NIST CSF “Protect” function.  
  - Implementation Details: Patch immediately; if patching is not feasible, isolate MOM servers and restrict external access.  

- **Document AI Companion Safety Controls for FTC Inquiry**  
  - Framework/Standard: COPPA, internal data-privacy programs.  
  - Implementation Details: Provide detailed records of data-collection flows, content moderation algorithms, and parental-consent mechanisms.  

- **Assess Solar-Powered IoT Devices for Undocumented Radios**  
  - Framework/Standard: Supply-chain risk-management (NIST SP 800-161).  
  - Implementation Details: Conduct hardware bill-of-materials (HBOM) review; disable undocumented radios; update procurement contracts to require component attestation.  

## Risk Management Developments

- **Risk Area**: Ransomware—UEFI Secure Boot Bypass (HybridPetya)  
  - Assessment Methods: Include firmware-level threat modeling and Secure Boot validation in risk assessments.  
  - Mitigation Strategies: Enforce UEFI firmware updates, enable Secure Boot attestation logging, and deploy EDR with boot-kit detection.  

- **Risk Area**: Mobile Spyware Targeting iOS Zero-Days  
  - Assessment Methods: High-risk user profiling, mobile-device forensics, and threat-intel monitoring.  
  - Mitigation Strategies: Rapid OS patching, deployment of MTD solutions, and user awareness on spear-phishing vectors.  

- **Risk Area**: Supply-Chain Software Vulnerabilities (Apriso, Cursor)  
  - Assessment Methods: SBOM review, third-party risk questionnaires, continuous scanning.  
  - Mitigation Strategies: Patch management, zero-trust network segmentation, and contractual security requirements for vendors.  

- **Risk Area**: Privacy & Child Safety in AI Companions  
  - Assessment Methods: Data-protection impact assessments (DPIAs) focused on minors.  
  - Mitigation Strategies: Age-verification gates, content-filtering audits, parental-control dashboards.  

- **Risk Area**: Free VPNs with Shady Security Practices  
  - Assessment Methods: Vendor due diligence, penetration testing of VPN tunnels.  
  - Mitigation Strategies: Prefer audited, RAM-only VPN services; enforce no-logs contractual clauses.  

## Governance and Oversight Changes

- **Board Cyber-Risk Oversight**  
  - Requirements: Boards must receive briefings on firmware-level threats (UEFI ransomware) and AI-related privacy exposures involving minors.  
  - Accountability: CISO and Chief Privacy Officer to provide quarterly risk updates and remediation status.  

- **Patch Management Governance**  
  - Requirements: Formalize requirements to patch KEV-listed vulnerabilities within mandated windows.  
  - Accountability: IT Operations, with audit verification by Internal Audit.  

- **AI Ethics & Compliance Committees**  
  - Requirements: Establish cross-functional committees overseeing AI companion product lines, ensuring alignment with FTC and privacy regulations.  
  - Accountability: Chief Ethics Officer and Head of Product.  

- **Supply-Chain Security Oversight**  
  - Requirements: Implement governance for hardware/software BoM transparency, particularly for IoT and industrial devices.  
  - Accountability: Chief Procurement Officer with support from Security Architecture.  

## Industry-Specific Impacts

- **Manufacturing & Industrial Automation**  
  - Sector-Specific Requirements: Immediate patching of DELMIA Apriso RCE; enhanced network isolation of MOM systems.  

- **Technology & Social Media Platforms**  
  - Sector-Specific Requirements: Produce FTC-compliant documentation on AI companion safety; implement robust parental-control frameworks.  

- **Mobile & Consumer Electronics**  
  - Sector-Specific Requirements: Fast-track iOS and Samsung security updates; integrate mobile threat monitoring for executives and journalists.  

- **Transportation & Critical Infrastructure**  
  - Sector-Specific Requirements: Audit solar-powered roadway devices for undocumented radios; update procurement policies to require device attestation.  

- **Healthcare & Public Sector (High-Risk Data Holders)**  
  - Sector-Specific Requirements: Conduct DPIAs for new AI companion deployments; enforce strict patch management for end-of-support Windows devices handling regulated data.  

- **Telecommunications & VPN Providers**  
  - Sector-Specific Requirements: Transition to RAM-only server architectures; undergo third-party privacy audits to rebuild consumer trust.  

**Bold** actions on patching, AI safety documentation, and firmware security are required in the near term to maintain compliance and reduce emerging cyber-risk exposure.