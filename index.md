# GRC Intelligence Report

Over the last week the security landscape has been dominated by a string of actively-exploited zero-day vulnerabilities, sophisticated multi-factor-authentication (MFA) bypass techniques, and renewed focus on supply-chain and open-source package integrity. Of particular note, Microsoft rushed out emergency patches for two SharePoint Server remote-code-execution (RCE) flaws (CVE-2025-53770/53771) that were already being weaponised to compromise at least 85 organisations, while Hewlett-Packard Enterprise (HPE) disclosed hard-coded administrative credentials in Aruba “Instant On” access points. Threat actors simultaneously resurfaced browser-based cryptojacking across 3,500 websites, hijacked popular npm linter packages via phishing-stolen tokens, and exploited a critical CrushFTP flaw (CVE-2025-54309). In identity security, the PoisonSeed campaign showed how FIDO2 hardware-key protections can be downgraded through QR-code phishing and WebAuthn cross-device abuse, underscoring MFA implementation risks. Web3 developers were separately targeted with the “Fickle Stealer” malware via fake AI tooling. Finally, new guidance on building foundation AI models highlighted the governance need for rigorous data provenance, bias testing, and alignment with existing risk-management frameworks. Collectively, these events emphasise the urgency of disciplined patch management, supply-chain vigilance, and board-level oversight of both cyber and AI-related risks.

## Regulatory Updates and Changes

### Microsoft SharePoint Emergency Security Update (CVE-2025-53770 & CVE-2025-53771)
- **Description**: Two zero-day RCE flaws in SharePoint Server exploited in “ToolShell” and related campaigns; Microsoft issued out-of-band patches and hardened configurations.  
- **Impact**: All organisations running on-premise SharePoint must immediately apply the cumulative update, review server logs for Indicators of Compromise (IoCs), and validate the integrity of uploaded files and workflows.  
- **Timeline**: Patches released 20 July 2025; exploitation observed since 18 July 2025.  
- **Affected Industries**: Any sector operating SharePoint (notably governmental, manufacturing, financial services, and professional services environments).  
- **Regulatory Body**: Microsoft Security Response Center (MSRC).

### HPE Security Bulletin – Aruba Instant On Access Points Hard-Coded Credentials
- **Description**: Critical flaw allows unauthenticated web-interface access on multiple Instant On models due to embedded username/password. HPE released firmware updates removing the credentials.  
- **Impact**: Customers must upgrade to the fixed firmware, rotate any reused credentials, and ensure management interfaces are not exposed to untrusted networks.  
- **Timeline**: Advisory and firmware published 19 July 2025.  
- **Affected Industries**: SMEs, retail, hospitality, and any organisation using Aruba Instant On Wi-Fi infrastructure.  
- **Regulatory Body**: Hewlett-Packard Enterprise PSIRT.

### CrushFTP Security Advisory (CVE-2025-54309)
- **Description**: Path-traversal flaw enables attackers to obtain admin-level access on unpatched CrushFTP servers (CVSS 9.0); active exploitation confirmed.  
- **Impact**: Immediate upgrade to the patched version, review of file-transfer logs, and revocation of compromised credentials.  
- **Timeline**: Vulnerability disclosed and patched 17 July 2025; exploitation ongoing.  
- **Affected Industries**: Managed-file-transfer service providers, healthcare, finance, and government entities using CrushFTP.  
- **Regulatory Body**: CrushFTP Security Team.

### npm Registry Security Notice – Hijacked Linter Packages
- **Description**: Threat actors injected malware into widely-used `eslint-config-prettier` and `eslint-plugin-prettier` after phishing maintainers and stealing npm tokens.  
- **Impact**: Development teams must audit dependency trees, replace malicious versions, rotate compromised access tokens, and implement 2FA for maintainer accounts.  
- **Timeline**: Malicious versions published 22 July 2025; taken down within 24 hours.  
- **Affected Industries**: All organisations that leverage the affected JavaScript libraries (especially software vendors and SaaS providers).  
- **Regulatory Body**: npm Security / GitHub.

### FIDO Alliance Security Alert – PoisonSeed MFA Downgrade
- **Description**: New phishing method tricks users into approving cross-device WebAuthn requests, effectively bypassing FIDO2 hardware keys.  
- **Impact**: Enforce origin validation, disable cross-device sign-in where unnecessary, and conduct user-education on QR-phishing scenarios.  
- **Timeline**: Campaign observed mid-July 2025.  
- **Affected Industries**: All sectors employing FIDO2/WebAuthn authentication.  
- **Regulatory Body**: FIDO Alliance (best-practice guidance).

## Compliance Requirements and Obligations

- **Mandatory SharePoint Patch Deployment**
  - **Framework/Standard**: Vendor security bulletin; aligns with typical vulnerability-management controls.
  - **Implementation Details**: Apply July 2025 cumulative update, enable audit logging, perform post-patch penetration testing.

- **Firmware Upgrade for Aruba Instant On**
  - **Framework/Standard**: IoT/OT security hardening guidelines.
  - **Implementation Details**: Install fixed firmware, isolate management VLANs, enforce strong unique credentials.

- **CrushFTP Version Update**
  - **Framework/Standard**: Secure file-transfer compliance (often referenced in HIPAA, PCI-DSS, and SOX control environments).
  - **Implementation Details**: Upgrade to latest release, enable encryption‐in‐transit, rotate user secrets.

- **Open-Source Dependency Integrity Checks**
  - **Framework/Standard**: Software-Bill-of-Materials (SBOM) best practices.
  - **Implementation Details**: Automate dependency scanning, lock package versions, enforce maintainer 2FA.

- **Enhanced MFA Configuration Against QR Phishing**
  - **Framework/Standard**: Identity-and-Access-Management control families.
  - **Implementation Details**: Disable cross-device sign-in if unused, prompt-based origin pinning, user awareness campaigns.

- **Cryptojacking Detection Controls**
  - **Framework/Standard**: Web-application security baselines.
  - **Implementation Details**: Integrate Content-Security-Policy (CSP) headers, leverage WebSocket monitoring, deploy behaviour-based browser-side detectors.

- **AI Foundation Model Governance**
  - **Framework/Standard**: Emerging AI-risk-management frameworks.
  - **Implementation Details**: Establish data-provenance documentation, formal bias/accuracy testing procedures, human-in-the-loop approval gates.

## Risk Management Developments

- **Supply-Chain Risk (Open-Source Packages)**
  - **Assessment Methods**: SBOM generation, dependency-health scoring, continuous monitoring of registries for hijacked packages.
  - **Mitigation Strategies**: Signed packages, mandatory maintainer MFA, rapid revocation of compromised tokens.

- **Zero-Day Exploitation Risk (SharePoint, CrushFTP)**
  - **Assessment Methods**: External attack-surface mapping, CVE prioritisation matrices, exploit-attempt telemetry.
  - **Mitigation Strategies**: Accelerated patching SLAs, virtual-patching (WAF rules) until fixed, segmentation of critical collaboration services.

- **Identity & Access Risk (FIDO2 Downgrade via QR Phishing)**
  - **Assessment Methods**: Phishing-resilience testing, MFA efficacy reviews, cross-device request monitoring.
  - **Mitigation Strategies**: Disable unused WebAuthn extensions, contextual authentication prompts, ongoing security-awareness training.

- **IoT Infrastructure Risk (Aruba Instant On)**
  - **Assessment Methods**: Device inventory reconciliation, credential-exposure scanning.
  - **Mitigation Strategies**: Firmware life-cycle management, zero-trust network segmentation for access points.

- **Cryptocurrency-Mining Abuse (Compromised Websites)**
  - **Assessment Methods**: Web integrity checksums, browser-side resource usage analytics.
  - **Mitigation Strategies**: Strict CSP, sub-resource integrity (SRI), and routine server-side malware sweeps.

- **AI Model-Building Risk**
  - **Assessment Methods**: Dataset licensing audits, adversarial testing for hallucinations and prompt injection.
  - **Mitigation Strategies**: Data governance committees, red-team exercises, ethical and privacy impact assessments.

## Governance and Oversight Changes

- **Board-Level Cyber Vulnerability Oversight**
  - **Requirements**: Directors must receive regular briefings on high-severity zero-days (e.g., SharePoint, CrushFTP) and ensure timely remediation budgets.
  - **Accountability**: CISO and CIO report patch-status metrics to Audit/Risk Committee.

- **Software-Supply-Chain Governance**
  - **Requirements**: Establish formal policies mandating SBOMs for all internally developed and third-party code.
  - **Accountability**: Chief Technology Officer (CTO) and Product Security Group oversee compliance.

- **Identity Governance**
  - **Requirements**: Periodic review of MFA configurations to prevent downgrade attacks; user-education KPIs.
  - **Accountability**: Identity-and-Access-Management (IAM) Program Owner.

- **AI Governance**
  - **Requirements**: Cross-functional AI Ethics Committee to approve foundation model development and ensure alignment with risk-management practices highlighted in recent industry guidance.
  - **Accountability**: Chief Data & AI Officer, with Audit Committee oversight.

## Industry-Specific Impacts

- **Technology & Software Development**
  - **Sector-Specific Requirements**: Immediate audit of npm dependencies; integration of secure-coding pipelines to catch malicious package updates.

- **Financial Services**
  - **Sector-Specific Requirements**: Accelerate SharePoint patching to protect customer data, align with sectoral incident-reporting obligations, tighten controls around WebAuthn MFA for online banking portals.

- **Healthcare & Life Sciences**
  - **Sector-Specific Requirements**: Remediate CrushFTP and SharePoint quickly to maintain patient-data confidentiality and avoid regulatory fines tied to protected-health-information exposure.

- **Education**
  - **Sector-Specific Requirements**: Prepare for adoption of AI-driven learning tools from major AI vendors by assessing data-privacy impacts and updating acceptable-use and safeguarding policies.

- **Retail & Hospitality (SMB)**
  - **Sector-Specific Requirements**: Patch Aruba Instant On access points, segregate POS networks, and monitor for cryptojacking scripts on e-commerce sites.

- **Web3 / Blockchain Development**
  - **Sector-Specific Requirements**: Harden developer endpoints, validate AI-based tooling sources, and educate on EncryptHub/Fickle Stealer phishing vectors targeting wallet credentials and private keys.

---

**Note**: Only information explicitly referenced in the provided articles has been included; no external regulation codes or framework versions have been introduced.