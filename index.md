# GRC Intelligence Report

A wave of security incidents and official advisories over the past week underscores converging pressures on governance, risk, and compliance programs. Healthcare and financial organizations absorbed major data-breach headlines, while cloud and SaaS providers faced heightened scrutiny following FBI and CISA notices. Legacy technology risk resurfaced with Microsoft’s 30-day end-of-support countdown for on-premises Exchange servers, and consumer-privacy controls gained renewed attention as disbursement of Facebook’s $725 million settlement begins. Meanwhile, hardware researchers demonstrated new memory-level attacks, and Microsoft’s plan to auto-install its AI Copilot application raised questions about software-deployment governance outside the European Economic Area. Collectively, these developments demand immediate action on third-party risk, insider-threat controls, vulnerability management, and board-level oversight of emerging technology deployments.

---

## Regulatory Updates and Changes

### CISA “Secure by Design” Guidance
- **Description**: Expanded guidance urging vendors and enterprises to integrate security features at every stage of product and infrastructure development.  
- **Impact**: Organizations are expected to demonstrate that security considerations are embedded in procurement, architecture, and development life cycles.  
- **Timeline**: Advisory is active; no firm deadline but immediate adoption is encouraged.  
- **Affected Industries**: All critical-infrastructure sectors, especially IT, healthcare, and finance.  
- **Regulatory Body**: Cybersecurity and Infrastructure Security Agency (CISA).

### FBI IC3 Alert on Threat Activity Against Salesforce Customers
- **Description**: The FBI’s Internet Crime Complaint Center (IC3) warned that threat groups UNC6040 and UNC6395 are harvesting Salesforce credentials and session tokens.  
- **Impact**: Companies must review access controls, threat-hunt for unauthorized log-ins, and enforce multi-factor authentication on all Salesforce tenants.  
- **Timeline**: Alert is effective immediately; FBI requests incident reporting “without delay.”  
- **Affected Industries**: Broad—finance, retail, manufacturing, and any entity with Salesforce deployments.  
- **Regulatory Body**: Federal Bureau of Investigation (FBI) – IC3.

### Microsoft Exchange 2016/2019 End-of-Support Notice
- **Description**: Microsoft confirmed that on-premises Exchange Server 2016 and 2019 reach end of extended support in 30 days.  
- **Impact**: Running unsupported software after that date may violate internal control frameworks and cyber-insurance conditions. Organizations must migrate to supported platforms or decommission servers.  
- **Timeline**: End-of-support occurs next month (30-day window from notice).  
- **Affected Industries**: All sectors operating on-premises Exchange, notably public sector, finance, and legal services.  
- **Regulatory Body**: Vendor notice (Microsoft) with direct compliance implications for regulated entities.

### Facebook $725 Million User-Privacy Settlement Disbursement
- **Description**: Court-approved settlement payments to eligible Facebook users for historical privacy violations have begun.  
- **Impact**: Sets a precedent for liability calculations tied to consumer data misuse and reinforces the need for robust privacy programs.  
- **Timeline**: Payment emails are being sent now; full disbursement schedule not publicly specified.  
- **Affected Industries**: Social-media, advertising, and any consumer-data-intensive business observing case law for privacy damages.  
- **Regulatory Body**: U.S. federal court (class-action oversight).

### Google Law Enforcement Request System (LERS) Security Incident Disclosure
- **Description**: Google confirmed a fraudulent account accessed its portal for official law-enforcement data requests.  
- **Impact**: Highlights obligations to verify requester identities and maintain strict access logs; may trigger breach-notification duties for agencies using the portal.  
- **Timeline**: Incident disclosed this week; remediation measures underway.  
- **Affected Industries**: Public-sector law enforcement agencies, technology providers handling legal requests.  
- **Regulatory Body**: Self-reported by Google; oversight likely by multiple jurisdictional authorities.

---

## Compliance Requirements and Obligations

- **Legacy Exchange Server Decommissioning**  
  - **Framework/Standard**: Vendor end-of-support guidance; aligns with internal control requirements for supported software.  
  - **Implementation Details**: Migrate mail services to cloud or newer on-prem versions; document change management and update asset registers.

- **Salesforce Tenant Hardening**  
  - **Framework/Standard**: FBI IC3 advisory alignment with identity-management best practices.  
  - **Implementation Details**: Enforce MFA, rotate credentials, enable login-forensics, and restrict API tokens.

- **Secure-by-Design Adoption**  
  - **Framework/Standard**: CISA guidance.  
  - **Implementation Details**: Incorporate threat modeling, secure coding standards, and supply-chain verification into SDLC checkpoints.

- **Insider-Threat Monitoring for Financial Institutions**  
  - **Framework/Standard**: Bank supervisory expectations for customer-data protection.  
  - **Implementation Details**: Deploy user-behavior analytics, implement strict post-employment access revocation, and conduct periodic insider-risk audits.

- **Ransomware Preparedness in Healthcare Supply Chains**  
  - **Framework/Standard**: Sector-specific patient-data protection obligations.  
  - **Implementation Details**: Validate third-party security posture, maintain offline backups, and test incident-response playbooks.

- **Automatic Software Deployment Governance (Microsoft 365 Copilot)**  
  - **Framework/Standard**: Change-management and privacy-consent policies.  
  - **Implementation Details**: Update governance charters to require opt-in/opt-out tracking, impact assessments, and user-communication plans before auto-installs.

- **Real-Time Vulnerability Intelligence Integration**  
  - **Framework/Standard**: Vulnerability-management best practices.  
  - **Implementation Details**: Subscribe to multi-source feeds, risk-rank alerts, and automate ticket creation for high-severity CVEs.

---

## Risk Management Developments

- **Supply-Chain Ransomware (KillSec attack on Brazilian healthcare vendor)**  
  - **Assessment Methods**: Third-party security questionnaires, continuous monitoring of vendor networks.  
  - **Mitigation Strategies**: Contractual security clauses, segmentation between vendor and patient-data systems, and cyber-insurance coverage review.

- **Cloud SaaS Credential Abuse (Salesforce)**  
  - **Assessment Methods**: Token enumeration checks, audit-log reviews.  
  - **Mitigation Strategies**: MFA enforcement, least-privilege role redesign, and API rate limiting.

- **Insider Threats (FinWise former employee breach)**  
  - **Assessment Methods**: Privileged-access baselines, anomaly detection on file-access patterns.  
  - **Mitigation Strategies**: Immediate off-boarding controls, data-loss-prevention tooling, and periodic insider-risk training.

- **Memory Hardware Exploits (Phoenix Rowhammer on DDR5)**  
  - **Assessment Methods**: Hardware-level penetration testing, firmware version verification.  
  - **Mitigation Strategies**: Deploy error-correcting memory options, enable available vendor mitigations, and monitor for abnormal bit-flip patterns.

- **USB Worm Propagation (SnakeDisk / Mustang Panda)**  
  - **Assessment Methods**: Endpoint scanning for unusual USB autorun activity.  
  - **Mitigation Strategies**: Disable autorun, enforce device control policies, and educate users on removable-media risks.

- **Automatic Software Deployment Risks (Microsoft 365 Copilot)**  
  - **Assessment Methods**: Change-impact assessments, user-experience testing.  
  - **Mitigation Strategies**: Staged rollouts, rollback plans, and data-collection transparency notices.

- **Law Enforcement Data-Portal Compromise (Google LERS)**  
  - **Assessment Methods**: Credential vetting audits, IP reputation checks.  
  - **Mitigation Strategies**: Strong authentication for requester accounts, continuous monitoring, and incident-response drills with public-sector partners.

---

## Governance and Oversight Changes

- **Board Oversight of Third-Party Risk**  
  - **Requirements**: Boards must regularly review supply-chain risk reports and ensure vendor-management frameworks are funded and enforced.  
  - **Accountability**: Chief Risk Officer (CRO) and vendor-management committees.

- **Executive Accountability for Privacy Settlements**  
  - **Requirements**: Senior leadership must certify adequacy of privacy controls and monitor compliance with settlement obligations.  
  - **Accountability**: Chief Privacy Officer (CPO) reporting quarterly to the board audit committee.

- **Legacy-System Governance**  
  - **Requirements**: Technology committees must approve decommission plans for unsupported systems and verify migration budgets.  
  - **Accountability**: Chief Information Officer (CIO) and internal audit.

- **Secure-by-Design Program Governance**  
  - **Requirements**: Establish cross-functional steering group to oversee adoption of CISA guidance and report progress metrics.  
  - **Accountability**: Chief Technology Officer (CTO) with quarterly board updates.

---

## Industry-Specific Impacts

- **Healthcare**  
  - Supply-chain ransomware elevates patient-data exposure risks.  
  - Providers must reinforce vendor-assessment processes and ensure rapid breach notification procedures.

- **Financial Services**  
  - Insider breach at FinWise Bank spotlights need for stringent off-boarding and privileged-user monitoring.  
  - Banks should reassess data-access governance and update incident-response playbooks.

- **Technology & Cloud SaaS**  
  - Salesforce credential-theft campaign demands immediate identity-management enhancements.  
  - Google LERS incident imposes stricter access-validation duties for law-enforcement data exchanges.

- **Public Sector / Law Enforcement**  
  - Compromise of data-request portals necessitates verification of digital-evidence chain-of-custody and reinforces multi-factor mandates.

- **Hardware & Semiconductor Manufacturers**  
  - Phoenix Rowhammer research indicates need for updated memory-protection designs and customer advisories on firmware patches.

- **Enterprise Productivity Software Users**  
  - Automatic deployment of Microsoft 365 Copilot requires change-management approvals and user-privacy impact assessments, particularly outside the EEA.

---

**End of Report**