# GRC Intelligence Report

Over the last reporting period, the threat and compliance landscape was dominated by security research disclosures, large-scale supply-chain and ransomware events, privacy-settlement follow-through, and imminent software end-of-life milestones. Key developments include a new “Phoenix” RowHammer technique that defeats current DDR5 defenses, a credential-stealing compromise of more than 40 npm packages, ransomware impacting a major Brazilian healthcare software vendor, and an insider breach at U.S.-based FinWise Bank. Google confirmed abuse of its Law-Enforcement Request System (LERS), while the FBI issued an IC3 alert on threat actors targeting Salesforce customers. Concurrently, Microsoft reminded organizations that Exchange Server 2016 and 2019 will exit extended support within 30 days, and Meta/Facebook has begun paying out its US $725 million privacy settlement. Collectively, these items elevate obligations around third-party risk management, data-protection controls, and executive oversight of software-lifecycle and privacy compliance programs.

## Regulatory Updates and Changes

### Microsoft Exchange 2016 & 2019 End-of-Extended-Support Notice
- **Description**: Microsoft reiterated that both on-premises Exchange Server versions will reach end of extended support next month; no further security patches will be published.  
- **Impact**: Organizations must migrate mail workloads to supported Exchange versions or cloud alternatives, and fully decommission legacy servers to remain patch-compliant.  
- **Timeline**: End of support occurs in 30 days from Microsoft’s advisory date.  
- **Affected Industries**: All sectors running on-premises Microsoft Exchange.  
- **Regulatory Body**: Microsoft Product Security & Compliance Group.

### Facebook US $725 Million Privacy Settlement
- **Description**: Settlement payments tied to Facebook’s 2022 class-action privacy case have entered the distribution phase.  
- **Impact**: Demonstrates enforcement momentum on large-scale privacy violations, reinforcing the need for robust data-governance programs and transparent user-consent practices.  
- **Timeline**: Payout notifications are being sent now; no future compliance deadline specified.  
- **Affected Industries**: Social-media platforms, online advertisers, data brokers.  
- **Regulatory Body**: U.S. District Court-supervised settlement administration.

### FBI IC3 Alert – Threat Actors Targeting Salesforce Customers
- **Description**: FBI Internet Crime Complaint Center (IC3) warned that UNC6040 and UNC6395 are conducting credential-harvesting and data-exfiltration campaigns against Salesforce tenants.  
- **Impact**: Requires immediate review of SaaS access controls, MFA enforcement, and API token management.  
- **Timeline**: Alert active; no explicit deadline.  
- **Affected Industries**: Any organization using Salesforce, especially marketing and customer-service functions.  
- **Regulatory Body**: Federal Bureau of Investigation (FBI) – IC3.

### Google Law-Enforcement Request System (LERS) Security Incident
- **Description**: Google confirmed that attackers created a fraudulent account within LERS, potentially enabling unauthorized data-request submissions.  
- **Impact**: Triggers reassessment of legal-process compliance procedures and third-party request validation workflows.  
- **Timeline**: Incident disclosed; Google conducting remediation.  
- **Affected Industries**: All entities receiving or issuing legal data-requests via Google.  
- **Regulatory Body**: Google Trust & Safety / Legal Compliance.

### FinWise Bank Insider Data-Breach Notification
- **Description**: FinWise disclosed that a former employee accessed sensitive American First Finance files affecting 689 k customers.  
- **Impact**: Obligates breach notifications and reinforces insider-risk controls under banking privacy mandates.  
- **Timeline**: Notification in effect; follow-up remediation ongoing.  
- **Affected Industries**: Financial services, fintech partners.  
- **Regulatory Body**: FinWise Bank compliance office (self-reported).

### Brazilian Healthcare Ransomware Event (KillSec)
- **Description**: KillSec ransomware compromised a “major element” of Brazil’s healthcare technology supply chain, stealing patient data.  
- **Impact**: Organizations handling health information must verify ransomware defenses, offline backups, and patient-data encryption.  
- **Timeline**: Incident currently under investigation.  
- **Affected Industries**: Healthcare providers, health-tech vendors in Brazil.  
- **Regulatory Body**: Not specified; investigation details pending.

## Compliance Requirements and Obligations

- **Legacy Server Decommissioning**  
  - **Framework/Standard**: Vendor Security Lifecycle / Patch-Management Best Practices  
  - **Implementation Details**: Remove Exchange 2016/2019 from production, migrate mailboxes, and disable external SMTP exposure before the support cutoff.

- **Supply-Chain Package Integrity for npm**  
  - **Framework/Standard**: NIST SSDF, OWASP Software Component Verification  
  - **Implementation Details**: Enforce signed packages, use lockfiles, continuous SCA scanning, and quarantine or replace compromised “bundle.js” artifacts.

- **DDR5 Hardware Attack Mitigations**  
  - **Framework/Standard**: ISO/IEC 27001 Annex A 8 (Physical & Environmental), hardware assurance guidance  
  - **Implementation Details**: Deploy memory–refresh rate tuning, error-correction monitoring, and, where feasible, row-hammer-aware memory controllers.

- **SaaS Access Hardening for Salesforce**  
  - **Framework/Standard**: CSA Cloud Controls Matrix (IAM, SIEM)  
  - **Implementation Details**: Enforce MFA on all roles, implement IP allow-listing, rotate OAuth tokens, and audit API logs for anomalous exports.

- **Legal-Process Request Validation**  
  - **Framework/Standard**: Corporate Law-Enforcement Response Policy  
  - **Implementation Details**: Introduce dual-control approval for all LERS submissions and verify authenticity via out-of-band channels.

- **Insider-Risk Monitoring**  
  - **Framework/Standard**: FFIEC Information-Security Handbook (for banks)  
  - **Implementation Details**: Automated account disablement on termination, DLP for file transfer, and role-based least privilege review.

- **Healthcare Ransomware Preparedness**  
  - **Framework/Standard**: Health-sector ransomware guidelines, ISO 27799  
  - **Implementation Details**: Immutable backups, segmentation of diagnostic networks, 24×7 SOC monitoring, and tabletop incident-response drills.

## Risk Management Developments

- **Hardware-Level Memory Corruption (DDR5 RowHammer)**  
  - **Assessment Methods**: Pen-test labs simulate “Phoenix” bit-flip patterns; integrate hardware fuzzing into threat-modeling.  
  - **Mitigation Strategies**: Firmware updates, error-correcting codes, increased refresh rates, and vendor partnership for next-gen mitigation chips.

- **Software Supply-Chain Compromise (npm)**  
  - **Assessment Methods**: Continuous SBOM generation and dependency-track analysis.  
  - **Mitigation Strategies**: Signed-package enforcement, automated dependency updates, and sandboxed build pipelines.

- **Ransomware on Critical Infrastructure (KillSec)**  
  - **Assessment Methods**: Sector-specific risk scoring, dwell-time analysis, and tabletop exercises.  
  - **Mitigation Strategies**: Zero-trust segmentation, immutable backups, incident-response retainer agreements.

- **Insider Threat (FinWise Case)**  
  - **Assessment Methods**: UEBA (User & Entity Behavior Analytics) and periodic privileged-access reviews.  
  - **Mitigation Strategies**: Immediate access revocation upon termination, DLP, and mandatory exit interviews.

- **SaaS Credential Phishing (Salesforce Campaigns)**  
  - **Assessment Methods**: Phishing-resilience testing, log-correlation of unusual IP geolocations.  
  - **Mitigation Strategies**: MFA enforcement, adaptive authentication, and API anomaly detection.

- **Abuse of Legal-Process Portals (Google LERS)**  
  - **Assessment Methods**: Policy compliance audits and traceability of data-request origin.  
  - **Mitigation Strategies**: Multi-factor, role-based access to portals and cross-verification of requests.

## Governance and Oversight Changes

- **Third-Party/Supply-Chain Governance**  
  - **Requirements**: Board-level review of open-source and SaaS dependencies; mandate SBOM reporting from vendors.  
  - **Accountability**: Chief Information Security Officer (CISO) and Procurement Committee.

- **Software End-of-Life Lifecycle Governance**  
  - **Requirements**: Establish formal EoL register and quarterly board reporting on unsupported systems.  
  - **Accountability**: CIO, with audit validation by Internal Audit.

- **Data-Privacy Settlement Oversight**  
  - **Requirements**: Strengthened privacy-by-design policies, user-consent tracking, and external privacy-impact assessments.  
  - **Accountability**: Chief Privacy Officer (CPO) reporting to the Risk Committee.

- **Incident-Response Governance**  
  - **Requirements**: Crisis-management playbooks inclusive of ransomware, supply-chain, and insider threat scenarios.  
  - **Accountability**: Enterprise Risk Management (ERM) team with quarterly board drills.

## Industry-Specific Impacts

- **Healthcare Technology**  
  - **Impacts**: Elevated ransomware risk; imperative to secure patient-record interfaces and enforce data-resiliency controls.  
  - **Sector-Specific Requirements**: Implement immutable backups and network segmentation of medical devices.

- **Financial Services**  
  - **Impacts**: Insider breach underscores the need for rigorous off-boarding and GLBA-aligned data-protection.  
  - **Sector-Specific Requirements**: Real-time DLP, FFIEC insider-risk monitoring, and regulatory breach notifications.

- **Software Development & DevOps**  
  - **Impacts**: npm compromise highlights necessity for secure build pipelines and SBOMs.  
  - **Sector-Specific Requirements**: Dependency-track monitoring, mandatory signed artifacts, and vulnerability disclosure processes.

- **SaaS / Cloud CRM Users**  
  - **Impacts**: FBI alert necessitates immediate Salesforce hardening.  
  - **Sector-Specific Requirements**: MFA for all CRM users, IP allow-listing, and continuous log analytics.

- **Social-Media Platforms**  
  - **Impacts**: Ongoing privacy settlement payments reinforce the cost of inadequate data-governance.  
  - **Sector-Specific Requirements**: Transparent data-collection notices and annual third-party privacy audits.

- **General Enterprise IT**  
  - **Impacts**: Exchange end-of-support demands resource allocation for migration projects.  
  - **Sector-Specific Requirements**: Decommission unsupported software and document residual risk acceptance if migration is delayed.

