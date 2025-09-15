# GRC Intelligence Report

The past week produced a concentrated burst of cybersecurity advisories and lifecycle notices that raise immediate governance, risk, and compliance (GRC) considerations. U.S. federal agencies (CISA and FBI) released multiple security alerts covering actively-exploited vulnerabilities in manufacturing software and widespread data-theft campaigns against Salesforce environments. Concurrently, Microsoft issued final reminders for the impending end-of-support dates for Windows 10 and Windows 11 23H2 Home/Pro editions, creating urgent software-lifecycle and patch-management obligations. The U.S. Federal Trade Commission (FTC) opened inquiries into the safety of AI “companion” products marketed to children, signalling heightened regulatory scrutiny of AI governance and child-privacy controls. National-level advisories from France’s CERT-FR highlighted recurring spyware campaigns against Apple devices, while Samsung and Cursor disclosed critical zero-day and configuration flaws that require immediate remediation. In parallel, new threat activity—VoidProxy phishing-as-a-service, WhiteCobra’s malicious VSCode extensions, and HybridPetya ransomware—expanded the risk landscape, underscoring the need for reinforced supply-chain controls, endpoint hardening, and identity-security measures.

---

## Regulatory Updates and Changes

### FTC Inquiry into AI Companion Safety for Minors
- **Description**: The U.S. Federal Trade Commission launched investigations into seven technology firms, including OpenAI and Meta, over reports that AI companion products expose children to inappropriate or harmful content.  
- **Impact**: Companies offering AI-driven chatbots or “companions” aimed at minors must review child-safety features, age-verification controls, data-collection practices, and content-moderation workflows. Documentation demonstrating compliance with child-privacy statutes is likely to be requested.  
- **Timeline**: Investigations are active; no statutory deadline was published.  
- **Affected Industries**: AI software providers, social-media platforms, EdTech vendors, toy and gaming companies integrating AI chat features.  
- **Regulatory Body**: U.S. Federal Trade Commission (FTC)

### Microsoft Windows 10 End-of-Support Notice
- **Description**: Microsoft reiterated that Windows 10 will reach end of support in 30 days, on October 14. Security updates will cease for all editions.  
- **Impact**: Organizations must migrate devices to a supported operating system or enroll in Microsoft’s paid Extended Security Updates (ESU) program to maintain compliance with internal and external security baselines.  
- **Timeline**: End of support — October 14 (30-day notice).  
- **Affected Industries**: All sectors running Windows 10 on desktops, laptops, kiosks, or operational technology.  
- **Regulatory Body**: Microsoft (vendor lifecycle notification)

### Microsoft Windows 11 23H2 Home/Pro End-of-Support Reminder
- **Description**: Microsoft advised that Windows 11 version 23H2 (Home and Pro) will stop receiving updates in 60 days, in November.  
- **Impact**: Similar to Windows 10, organizations must upgrade to a supported build or use ESUs to align with patch-management and cyber-hygiene requirements.  
- **Timeline**: End of support — November (60-day notice).  
- **Affected Industries**: All sectors using Windows 11 23H2 Home/Pro.  
- **Regulatory Body**: Microsoft

### CISA Advisory on DELMIA Apriso Remote Code Execution Flaw
- **Description**: CISA warned that threat actors are actively exploiting a critical remote code execution vulnerability in Dassault Systemes’ DELMIA Apriso manufacturing-operations platform.  
- **Impact**: Manufacturers must apply the vendor-supplied patch and validate that exposed MOM servers are not publicly accessible. Exploitation may trigger mandatory incident reporting under sectoral regulations.  
- **Timeline**: Advisory issued this week; patch available immediately.  
- **Affected Industries**: Manufacturing, automotive, aerospace, and any enterprises running DELMIA Apriso.  
- **Regulatory Body**: Cybersecurity and Infrastructure Security Agency (CISA)

### FBI Flash Alert on UNC6040 & UNC6395 Targeting Salesforce
- **Description**: The FBI released indicators of compromise (IoCs) linked to two cyber-criminal groups stealing data from Salesforce environments through credential abuse and API exploitation.  
- **Impact**: Organizations using Salesforce must ingest IoCs into SIEM systems, monitor abnormal API calls, enforce MFA, and conduct credential hygiene reviews.  
- **Timeline**: Flash alert issued; no end date.  
- **Affected Industries**: All Salesforce customers, notably retail, healthcare, and financial services with large CRM deployments.  
- **Regulatory Body**: Federal Bureau of Investigation (FBI)

### CERT-FR Advisory on Recurring Apple Spyware Campaigns
- **Description**: France’s national CERT confirmed a fourth spyware campaign in 2025 targeting Apple devices via a disclosed zero-day vulnerability, affecting “targeted individuals.”  
- **Impact**: French organizations must disseminate Apple security updates promptly, review mobile-device-management (MDM) policies, and notify at-risk executives or activists.  
- **Timeline**: Alerts sent on September — (exact date specified as “last month”).  
- **Affected Industries**: Government, journalism, NGOs, and enterprises with high-risk executives in France.  
- **Regulatory Body**: CERT-FR (France)

### Samsung Security Update for CVE-2025-21043
- **Description**: Samsung patched a critical Android vulnerability (CVE-2025-21043) already exploited in zero-day attacks.  
- **Impact**: Mobile-device fleet managers must push the September security update and verify patch compliance for all Samsung devices.  
- **Timeline**: Patch released in the monthly update cycle (September).  
- **Affected Industries**: All sectors with corporate-issued or BYOD Samsung Android devices.  
- **Regulatory Body**: Samsung (vendor advisory)

---

## Compliance Requirements and Obligations

- **End-of-Life Migration**  
  - **Framework/Standard**: ISO 27001 Patch-Management & Asset-Management controls  
  - **Implementation Details**: Inventory Windows 10 and Windows 11 23H2 assets; schedule OS upgrades or enroll in ESU; update asset register and risk treatment plan.

- **Child-Privacy and AI Safety Controls**  
  - **Framework/Standard**: FTC guidelines; (potentially) Children’s Online Privacy Protection Act (COPPA)  
  - **Implementation Details**: Add parental consent workflows, age gating, content-moderation filters, and third-party auditing for AI products aimed at minors.

- **Salesforce Environment Hardening**  
  - **Framework/Standard**: NIST CSF Identity & Access Management (PR.AC)  
  - **Implementation Details**: Enforce MFA, limit API tokens, integrate FBI-provided IoCs into detection logic, and conduct credential-stuffing simulations.

- **Critical Patch Deployment – CVE-2025-21043 (Samsung)**  
  - **Framework/Standard**: CIS Mobile Device Benchmark  
  - **Implementation Details**: Push over-the-air update, verify installation via MDM, and maintain patch-compliance metrics.

- **Industrial Software Vulnerability Mitigation – DELMIA Apriso**  
  - **Framework/Standard**: IEC 62443-3-3 (System Security Requirements)  
  - **Implementation Details**: Apply vendor patch, segment MOM servers, validate least-privilege service accounts, and update software bill-of-materials (SBOM).

- **VSCode Extension Supply-Chain Control**  
  - **Framework/Standard**: NIST SP 800-218 Secure Software Development Framework  
  - **Implementation Details**: Restrict marketplace sources, conduct code-signing verification, and deploy runtime detection for malicious extensions.

---

## Risk Management Developments

- **Risk Area**: Phishing-as-a-Service (VoidProxy)  
  - **Assessment Methods**: Monitor proxy-based phishing indicators, conduct simulated adversary-in-the-middle MFA bypass tests.  
  - **Mitigation Strategies**: Implement FIDO2/WebAuthn phishing-resistant authentication, deploy secure web gateways with real-time URL rewriting.

- **Risk Area**: Supply-Chain Compromise via IDE Extensions (WhiteCobra)  
  - **Assessment Methods**: SBOM analysis of developer environments, periodic marketplace scanning.  
  - **Mitigation Strategies**: Enforce allow-lists for approved extensions, integrate endpoint detection for developer workstations.

- **Risk Area**: Ransomware with Firmware-Level Techniques (HybridPetya)  
  - **Assessment Methods**: UEFI integrity checks, bootloader verification logs.  
  - **Mitigation Strategies**: Enable Secure Boot with hardware attestation, maintain offline backups insulated from EFI partitions.

- **Risk Area**: Zero-Day Mobile Exploits (Samsung, Apple Spyware)  
  - **Assessment Methods**: Mobile threat-defense telemetry, anomaly detection on zero-day exploit patterns.  
  - **Mitigation Strategies**: Rapid patch deployment, restrict sideloading, enforce device-certificate validation.

- **Risk Area**: Configuration-Driven Code Execution (Cursor Editor Flaw)  
  - **Assessment Methods**: Static analysis of user workspace configurations, red-team exploitation testing.  
  - **Mitigation Strategies**: Apply vendor fixes, disable auto-execution of commands by default, educate developers on secure configuration.

---

## Governance and Oversight Changes

- **Software Lifecycle Governance**  
  - **Requirements**: Boards must ensure policies mandate migration off unsupported OS versions before vendor deadlines.  
  - **Accountability**: CIO/CTO for planning; CISO for residual-risk acceptance approval.

- **AI Ethics and Child-Safety Oversight**  
  - **Requirements**: Establish an AI Risk Committee tasked with reviewing child-focused AI products in light of FTC scrutiny.  
  - **Accountability**: Chief Ethics Officer or equivalent; periodic reporting to Board Audit/Risk Committee.

- **Third-Party SaaS Governance (Salesforce)**  
  - **Requirements**: Strengthen vendor-risk assessments and SOC2 review cadence for critical SaaS platforms.  
  - **Accountability**: Vendor-Management Office and Data-Protection Officer.

- **Industrial Control System (ICS) Security Governance**  
  - **Requirements**: Integrate OT security posture into enterprise risk dashboards following CISA’s Apriso alert.  
  - **Accountability**: VP of Manufacturing Operations partnering with CISO.

---

## Industry-Specific Impacts

- **Manufacturing**  
  - **Sector-Specific Requirements**: Patch DELMIA Apriso immediately; review segmentation of MOM systems; maintain ICS incident-response playbooks.

- **Technology & Software Development**  
  - **Sector-Specific Requirements**: Audit IDE extensions (VSCode/Open VSX); enforce secure software-supply-chain controls; remediate Cursor editor vulnerability.

- **Retail, Healthcare, Financial Services**  
  - **Sector-Specific Requirements**: Ingest FBI IoCs for Salesforce, verify customer-data access logs, and implement transaction-level anomaly detection.

- **Telecommunications & Mobility**  
  - **Sector-Specific Requirements**: Roll out Samsung September patch, monitor for mobile zero-day exploits; educate users on spyware risks.

- **Education & Child-Focused Services**  
  - **Sector-Specific Requirements**: Review AI companion deployments, ensure parental-consent mechanisms, update privacy notices to align with FTC expectations.

---

**Bold** action on patches, AI-safety controls, and software-lifecycle governance will be needed over the next 30–60 days to maintain compliance and manage elevated cyber risk.