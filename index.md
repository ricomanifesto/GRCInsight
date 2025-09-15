# GRC Intelligence Report  

Recent security alerts from U.S. and European authorities signal heightened regulatory and supervisory attention on software-supply-chain security, artificial-intelligence safety for minors, and the protection of cloud SaaS data.  The U.S. FTC has opened simultaneous inquiries into seven large AI-companion providers, while the FBI and CISA issued FLASH and KEV notices addressing active exploitation of Salesforce environments and critical manufacturing software vulnerabilities.  Microsoft’s hard end-date for Windows 10 support (14 Oct) introduces an immediate compliance deadline for organizations that have not completed migration planning.  Multiple threat-intel reports—covering new phishing-as-a-service (VoidProxy), malicious PyPI/VScode packages, and ransomware capable of bypassing UEFI Secure Boot—underscore the need for reinforced risk-management controls and stronger board-level oversight of third-party software intake, SaaS configurations, and legacy-system decommissioning.  

## Regulatory Updates and Changes  

### FTC Investigation into AI Companion Safety for Kids  
- **Description**: The U.S. Federal Trade Commission has launched investigations into seven technology firms (including OpenAI and Meta) to assess whether AI “companion” products marketed to children pose safety, privacy, or deceptive-practice concerns.  
- **Impact**: Companies offering AI chat or companion services must be prepared to evidence due-diligence around child-safety testing, transparent data-handling, and age-appropriate design practices.  
- **Timeline**: Investigations are open; no statutory deadlines disclosed.  
- **Affected Industries**: Artificial-intelligence platforms, social media, consumer software.  
- **Regulatory Body**: U.S. Federal Trade Commission (FTC).  

### FBI FLASH Alert – UNC6040 & UNC6395 Targeting Salesforce  
- **Description**: FBI FLASH alert shares indicators of compromise tied to two threat clusters stealing data from Salesforce tenants and extorting victims.  
- **Impact**: Organizations using Salesforce must review access-logs, IP restrictions, and API tokens; deploy MFA on admin accounts; and report suspected compromise to the FBI.  
- **Timeline**: Alert issued; mitigation recommended immediately.  
- **Affected Industries**: All sectors leveraging Salesforce, with emphasis on organizations storing large customer datasets.  
- **Regulatory Body**: Federal Bureau of Investigation (FBI).  

### CISA KEV Inclusion – DELMIA Apriso Remote Code Execution  
- **Description**: CISA warns that a critical RCE flaw in Dassault’s DELMIA Apriso manufacturing-operations-management platform is being actively exploited.  
- **Impact**: Federal civilian agencies and private manufacturers need to apply vendor patches, validate network segmentation, and monitor for anomalous outbound traffic from MOM servers.  
- **Timeline**: Added to Known Exploited Vulnerabilities (KEV) catalog; organizations must follow CISA’s standard remediation urgency (no specific date provided in article).  
- **Affected Industries**: Manufacturing, industrial automation, supply-chain logistics.  
- **Regulatory Body**: Cybersecurity and Infrastructure Security Agency (CISA).  

### Microsoft Windows 10 End-of-Support Notice  
- **Description**: Microsoft reiterated that Windows 10 security updates end on 14 Oct, after which only paid Extended Security Updates (ESU) will be offered.  
- **Impact**: Enterprises must migrate to Windows 11 or enroll in ESU to maintain supported status; failure may breach internal IT-security baselines and industry cyber-hygiene requirements.  
- **Timeline**: End-of-support takes effect 14 October (30 days from article date).  
- **Affected Industries**: All sectors running Windows 10 endpoints or operational technology.  
- **Regulatory Body**: Microsoft (vendor requirement affecting compliance postures).  

### CERT-FR Advisory on Apple-Targeted Spyware  
- **Description**: France’s CERT-FR published an advisory detailing exploitation of a recently disclosed Apple zero-day used in “sophisticated” spyware attacks.  
- **Impact**: French organizations are urged to apply Apple security patches and review mobile-device-management (MDM) policies to protect high-risk personnel.  
- **Timeline**: Advisory released; patches available now.  
- **Affected Industries**: Government, journalism, human-rights NGOs, and any entity with high-value mobile users.  
- **Regulatory Body**: CERT-FR (French national CERT).  

## Compliance Requirements and Obligations  

- **Patch Management for DELMIA Apriso**  
  - **Framework/Standard**: CISA KEV / general vulnerability-management controls  
  - **Implementation Details**: Apply Dassault’s security update; verify patch success via version checks; document remediation in vulnerability tracker.  

- **Salesforce Security Hardening**  
  - **Framework/Standard**: NIST CSF PR.AC, CSA STAR best practices  
  - **Implementation Details**: Enforce MFA, restrict API tokens, enable IP-allow-listing, and conduct weekly audit-log reviews for anomalous exports.  

- **Windows 10 Migration or ESU Enrollment**  
  - **Framework/Standard**: CIS Benchmarks, ISO 27001 A.12.6.1 (technical vulnerability management)  
  - **Implementation Details**: Complete endpoint inventory, schedule OS upgrades, or purchase ESU licenses; update asset register and risk treatment plans.  

- **AI Safety & Child-Protection Controls**  
  - **Framework/Standard**: FTC Act §5 (unfair/deceptive practices), emerging AI-governance policies  
  - **Implementation Details**: Perform child-impact assessments, implement content-filtering, publish transparent data-usage disclosures, and establish incident-reporting channels for harmful interactions.  

- **Mobile Zero-Day Response**  
  - **Framework/Standard**: ISO 27001 A.12.5 (installation of software on operational systems)  
  - **Implementation Details**: Push urgent iOS/iPadOS/watchOS updates, enforce device encryption, and disable unneeded message-preview features for high-risk users.  

## Risk Management Developments  

- **Supply-Chain Software Risk**  
  - **Assessment Methods**: Continuous monitoring of public code repositories (PyPI, VSCode Marketplace) for malicious packages; SBOM validation.  
  - **Mitigation Strategies**: Implement signed package policies, restrict developer installation privileges, and integrate automated dependency-scanning tools.  

- **SaaS Data Exfiltration & Extortion**  
  - **Assessment Methods**: Log-correlation of SaaS API calls, anomaly detection on data-export volumes.  
  - **Mitigation Strategies**: Enforce least-privilege roles, conditional access policies, AES-256 data-at-rest encryption, and cyber-insurance coverage review.  

- **Advanced Phishing-as-a-Service (VoidProxy)**  
  - **Assessment Methods**: Phish-simulation testing, credential-stuffing monitoring, and analysis of reverse-proxy traffic patterns.  
  - **Mitigation Strategies**: Implement FIDO2 hardware-based MFA, real-time phishing-site takedown services, and employee awareness refreshers.  

- **Legacy Systems Exposure (Windows 10 EoS)**  
  - **Assessment Methods**: Asset life-cycle mapping, vulnerability scanning for unsupported OS signatures.  
  - **Mitigation Strategies**: Segmentation of legacy devices, endpoint replacement budgeting, and ESU cost-benefit analysis.  

- **Ransomware Capable of UEFI Secure Boot Bypass (HybridPetya)**  
  - **Assessment Methods**: UEFI integrity checks, baseline comparison of EFI System Partitions.  
  - **Mitigation Strategies**: Enable measured-boot logging, maintain offline backups, restrict privileged firmware-update rights.  

## Governance and Oversight Changes  

- **Board-Level Cyber-Risk Oversight**  
  - **Requirements**: Regular briefings on FBI/CISA alerts, assurance that SaaS and supply-chain risks are incorporated into enterprise risk registers.  
  - **Accountability**: CISO to report quarterly to Audit & Risk Committee; CIO responsible for Windows 10 migration milestones.  

- **AI Governance Committees**  
  - **Requirements**: Establish cross-functional AI Ethics & Safety Committee to monitor FTC developments and implement child-safety controls.  
  - **Accountability**: Chief Privacy Officer (CPO) and Chief Product Officer jointly oversee compliance with emerging AI companion guidance.  

- **Patch and Vulnerability Governance**  
  - **Requirements**: Adopt 14-day remediation SLA for KEV-listed vulnerabilities per CISA recommendations.  
  - **Accountability**: Vulnerability-Management Team under VP Infrastructure.  

## Industry-Specific Impacts  

- **Manufacturing**  
  - **Sector-Specific Requirements**: Immediate patching of DELMIA Apriso; review segmentation of manufacturing execution systems to limit lateral movement.  

- **Cloud/SaaS Providers & Users**  
  - **Sector-Specific Requirements**: Strengthen tenant-level logging, implement zero-trust policies for Salesforce and Microsoft 365 environments.  

- **Artificial Intelligence & Social Platforms**  
  - **Sector-Specific Requirements**: Conduct child-safety impact assessments, document model-training data provenance, and prepare for potential FTC consent decrees.  

- **Software Development & IDE Ecosystem**  
  - **Sector-Specific Requirements**: Enforce signed-extension policies in VSCode/Cursor environments; integrate repository reputation scoring into CI/CD pipelines.  

- **Public Sector & Critical Infrastructure**  
  - **Sector-Specific Requirements**: Follow CISA KEV deadlines; report exploitation incidents through federal reporting channels; align with NIST IR guidelines for mobile zero-day threats.