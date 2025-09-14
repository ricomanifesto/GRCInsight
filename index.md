# GRC Intelligence Report

Over the last week, government agencies and security researchers issued several high-priority alerts that materially shift the Governance, Risk, and Compliance (GRC) landscape.  The U.S. Federal Trade Commission opened a new investigation into seven major technology firms over AI “companion” products marketed to minors, heightening regulatory exposure around child-safety, privacy, and algorithmic transparency.  Meanwhile, the FBI, CISA, CERT-FR, and Microsoft collectively published urgent security notices: (1) a flash alert on two threat clusters actively stealing data from Salesforce tenants; (2) a CISA-listed remote-code-execution flaw in Dassault’s DELMIA Apriso platform; (3) France’s fourth advisory this year on iOS spyware; and (4) a 60-day end-of-support countdown for Windows 11 23H2 Home and Pro editions.  At the vendor level, Samsung fixed an exploited Android zero-day (CVE-2025-21043), researchers disclosed HybridPetya ransomware’s ability to bypass UEFI Secure Boot, and multiple studies revealed insecure free VPN ecosystems and undocumented radios in solar-powered highway devices.  Collectively, these developments compel organizations to tighten third-party SaaS controls, accelerate patch-and-update cycles, refresh incident-response playbooks, and strengthen board-level oversight of emerging AI safety and OT/ICS risks.

---

## Regulatory Updates and Changes

### FTC Investigation into AI Companion Safety for Kids
- **Description**: The U.S. Federal Trade Commission has launched an investigation into seven technology companies, including OpenAI and Meta, focusing on whether AI “companion” applications adequately protect children from harmful content and data misuse.  
- **Impact**: Companies deploying AI chat or companion features must prepare for enhanced disclosure demands, implement stricter age-verification, parental-control, and content-moderation measures, and maintain auditable records of model training data.  
- **Timeline**: Formal investigative requests have been issued; additional compliance deadlines will follow as the investigation progresses.  
- **Affected Industries**: Social media, generative AI providers, EdTech, consumer electronics with AI assistants.  
- **Regulatory Body**: U.S. Federal Trade Commission (FTC)

### FBI Flash Alert: UNC6040 & UNC6395 Targeting Salesforce Platforms
- **Description**: The FBI distributed a flash alert containing indicators of compromise (IoCs) for two cyber-criminal groups exploiting misconfigured or unpatched Salesforce environments to exfiltrate sensitive customer data.  
- **Impact**: Organizations using Salesforce must ingest the IoCs, review access-control lists, enable multi-factor authentication, and apply Salesforce-recommended security settings.  
- **Timeline**: Alert issued; mitigations should be applied immediately.  
- **Affected Industries**: All sectors leveraging Salesforce, especially finance, healthcare, and retail.  
- **Regulatory Body**: Federal Bureau of Investigation (FBI)

### CERT-FR Advisory: Apple Spyware Campaign (Fourth in 2025)
- **Description**: CERT-FR confirmed Apple’s notification to French users about a sophisticated spyware campaign exploiting an iOS zero-day vulnerability to surveil targeted individuals.  
- **Impact**: French organizations should ensure all iOS devices are updated to the latest patched version, enable automatic updates, and monitor for abnormal outbound traffic.  
- **Timeline**: Notifications sent 5 Sept 2025; patch already released by Apple.  
- **Affected Industries**: Government, journalism, NGOs, and enterprises with high-risk mobile fleets in France.  
- **Regulatory Body**: Computer Emergency Response Team – France (CERT-FR)

### CISA Alert: Actively Exploited Dassault DELMIA Apriso RCE Vulnerability
- **Description**: CISA added a critical remote-code-execution flaw affecting DELMIA Apriso manufacturing-operations-management software to its Known Exploited Vulnerabilities (KEV) catalog.  
- **Impact**: Federal agencies and contractors must patch or implement vendor-recommended mitigations; private-sector manufacturers should follow suit to avoid ransomware or production disruption.  
- **Timeline**: Added to KEV 13 Sept 2025; agencies typically have 21 days to remediate once listed.  
- **Affected Industries**: Manufacturing, aerospace, automotive supply chains.  
- **Regulatory Body**: U.S. Cybersecurity and Infrastructure Security Agency (CISA)

### Microsoft End-of-Support Notice: Windows 11 23H2 Home and Pro
- **Description**: Microsoft reminded customers that Windows 11 Version 23H2 Home & Pro editions will stop receiving security updates in November 2025.  
- **Impact**: Enterprises must migrate endpoints to a supported build to remain compliant with vulnerability-management policies and many cyber-insurance requirements.  
- **Timeline**: 60 days remaining from the notice date; support ends November 2025.  
- **Affected Industries**: All sectors running Windows endpoints.  
- **Regulatory Body**: Microsoft (vendor policy; relevant to compliance frameworks that mandate supported software)

### Samsung Security Bulletin: CVE-2025-21043 Zero-Day
- **Description**: Samsung’s September Android security bulletin patched CVE-2025-21043, a vulnerability already exploited in the wild.  
- **Impact**: Mobile-fleet operators must push the latest firmware to all Samsung devices and review MDM policies.  
- **Timeline**: Patch released; immediate deployment advised.  
- **Affected Industries**: Any organization with Samsung Android devices, notably finance, healthcare, and government.  
- **Regulatory Body**: Samsung Mobile Security (vendor bulletin acknowledged by NIST NVD)

---

## Compliance Requirements and Obligations

- **Patch CVE-2025-21043 on Samsung Devices**  
  - Framework/Standard: Mobile device management best practices; ISO/IEC 27001 patch management clause.  
  - Implementation Details: Deploy September security update via MDM; verify firmware version in compliance dashboards.

- **Upgrade Windows 11 23H2 Systems Before November 2025**  
  - Framework/Standard: CIS Controls v8 (Safeguard 7.3); PCI DSS 4.0 (Requirement 6).  
  - Implementation Details: Transition to 24H2 or later; document upgrade plan and residual-risk acceptance for any exceptions.

- **Apply CISA KEV-Mandated Patches for DELMIA Apriso RCE**  
  - Framework/Standard: U.S. Federal Binding Operational Directive (BOD) 22-01.  
  - Implementation Details: Identify affected servers, test vendor patch, or isolate systems until remediation.

- **Implement FBI IoCs for Salesforce Threat Activity**  
  - Framework/Standard: NIST SP 800-53 (IR-4, SI-4).  
  - Implementation Details: Ingest IoCs into SIEM, enable event monitoring API logs, enforce MFA and IP allow-listing.

- **Strengthen AI Companion Safety Controls Under FTC Scrutiny**  
  - Framework/Standard: COPPA (Children’s Online Privacy Protection Act).  
  - Implementation Details: Conduct data-protection impact assessments, integrate parental dashboards, and log model outputs for auditability.

- **Validate iOS Devices Against CERT-FR Spyware Indicators**  
  - Framework/Standard: E.U. NIS2 directive (for European operators of essential services).  
  - Implementation Details: Enforce minimum iOS version, disable sideloading profiles, and monitor EDR alerts.

- **Disable Auto-Execution Feature in Cursor Terminal**  
  - Framework/Standard: Secure‐by-default coding guidelines (OWASP).  
  - Implementation Details: Update to fixed Cursor release; set “Trusted Prompts” to manual approval in developer workstations.

---

## Risk Management Developments

- **Third-Party SaaS Data Theft (Salesforce)**  
  - Assessment Methods: Continuous monitoring of SaaS API logs; threat-intel correlation with FBI IoCs.  
  - Mitigation Strategies: Enforce least-privilege roles, conditional access, and threat-detection rules tuned for mass-data exports.

- **UEFI-Level Ransomware (HybridPetya)**  
  - Assessment Methods: Include firmware integrity checks in vulnerability scans; verify Secure Boot status.  
  - Mitigation Strategies: Update UEFI firmware, enable TPM-backed secure-boot keys, and maintain offline recovery images.

- **OT/ICS Vulnerabilities (DELMIA Apriso & Undocumented Radios in Solar Devices)**  
  - Assessment Methods: Conduct network-segment audits and passive asset discovery; review SBOMs from vendors.  
  - Mitigation Strategies: Patch management windows aligned with production downtime, install network intrusion detection on industrial segments, and disable undocumented wireless interfaces.

- **Mobile Zero-Days (Samsung, iOS Spyware)**  
  - Assessment Methods: Mobile-threat-defense (MTD) telemetry; compliance attestation in MDM.  
  - Mitigation Strategies: Enforce rapid-patch SLAs (<72 hours), restrict high-risk apps, and educate users on phishing vectors.

- **End-of-Support Software Exposure (Windows 11 23H2)**  
  - Assessment Methods: Asset-lifecycle inventories and vulnerability scanning for unsupported OS.  
  - Mitigation Strategies: Expedite upgrades, isolate legacy systems, and update cyber-insurance disclosures.

- **Insecure Consumer VPN Ecosystem**  
  - Assessment Methods: Vendor-risk assessments; penetration testing of VPN app traffic.  
  - Mitigation Strategies: Whitelist only vetted VPNs, require TLS 1.3 and audited no-log policies, and block suspicious VPN domains at the firewall.

---

## Governance and Oversight Changes

- **AI Governance for Child-Safety**  
  - Requirements: Establish cross-functional AI ethics committee to oversee model deployment and compliance with FTC inquiries.  
  - Accountability: Chief Privacy Officer and Chief AI Officer report quarterly to the Board Risk Committee.

- **Patch-Management Governance**  
  - Requirements: Adopt 21-day remediation window for any vulnerabilities added to CISA KEV list.  
  - Accountability: CIO retains ultimate responsibility; Internal Audit validates adherence semi-annually.

- **Mobile-Fleet Oversight**  
  - Requirements: Board-approved mobile-device policy mandating installation of vendor patches within 72 hours of release.  
  - Accountability: CISO and Enterprise Mobility Manager; compliance evidenced in monthly KPI dashboard.

- **ICS/OT Risk Governance**  
  - Requirements: Create dedicated OT Security Steering Group; align with NIST SP 800-82 guidance.  
  - Accountability: VP of Operations and CISO jointly own risk register and capex requests for OT security controls.

---

## Industry-Specific Impacts

- **Manufacturing**  
  - Sector-Specific Requirements: Patch DELMIA Apriso immediately; segment production networks; implement firmware whitelisting to counter HybridPetya.

- **Technology & AI Providers**  
  - Sector-Specific Requirements: Document training datasets, implement child-safety guardrails, and prepare for potential FTC consent decrees.

- **Financial Services**  
  - Sector-Specific Requirements: Review Salesforce user roles and API tokens against FBI IoCs; ensure mobile-device EDR coverage for executives.

- **Healthcare**  
  - Sector-Specific Requirements: Validate Samsung and Apple device patches to maintain HIPAA Security Rule compliance; scrutinize third-party VPN usage for telehealth.

- **Transportation & Critical Infrastructure**  
  - Sector-Specific Requirements: Audit solar-powered roadway devices for undocumented radios; follow CISA advisories for OT asset inventory.

- **Public Sector / Government Contractors**  
  - Sector-Specific Requirements: Comply with BOD 22-01 timelines for KEV vulnerabilities; transition all Windows 11 systems to supported builds before November 2025.

---

**End of Report**