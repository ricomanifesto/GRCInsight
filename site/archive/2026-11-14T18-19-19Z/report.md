# GRC Intelligence Report - 2026-11-14
**Generated:** 2026-11-14T18:19:19.514719Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/30be4ff61c5a4cab6cacccb166301360a05b3404/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-14](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Active exploitation of critical vulnerabilities and cloud infrastructure weaknesses demands immediate control validation. CISA added an actively exploited UnrealIRCd flaw to its Known Exploited Vulnerabilities catalog, while research disclosed attacks allowing malicious hosts to breach AMD SEV-SNP confidential VMs and Check Point gateways to deploy destructive wipers on ESXi hosts. Vulnerability management, data protection, and monitoring owners must confirm asset coverage, cloud provider assurances, and detection capabilities for these active threat vectors. [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html); [New Mior and Skyfall Attacks Let Rogue Cloud Hosts Steal Secrets From AMD SEV-SNP VMs](https://thehackernews.com/2026/11/new-mior-and-skyfall-attacks-let-rogue.html); [Check Point gateways hacked via PHP2Shell to deploy VMware ESXi wiper](https://www.bleepingcomputer.com/news/security/check-point-gateways-hacked-via-php2shell-to-deploy-vmware-esxi-wiper/)

Supply chain compromises and AI-driven identity risks expand the attack surface beyond traditional boundaries. A credential theft at Fireworks AI enabled malicious extension distribution through the Cursor marketplace, and an AI agent was manipulated to alter financial transactions without triggering alerts. Meanwhile a defense contractor detected a cyberattack disrupting military drone operations. Third-party risk, access management, and incident response owners should verify supplier assurance, AI agent permissions, and containment readiness for these emerging vectors. [Cursor confirms security breach led to malicious Claude Code extension](https://www.bleepingcomputer.com/news/security/cursor-confirms-security-breach-led-to-malicious-claude-code-extension/); [How one AI agent exposed five critical enterprise security gaps](https://www.bleepingcomputer.com/news/security/how-one-ai-agent-exposed-five-critical-enterprise-security-gaps/); [German military drone operations disrupted by cyberattack](https://www.bleepingcomputer.com/news/security/german-military-drone-operations-disrupted-by-cyberattack/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### UnrealIRCd added to CISA Known Exploited Vulnerabilities catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** The KEV catalog addition signals active exploitation requiring immediate asset identification and remediation. Vulnerability owners should confirm whether UnrealIRCd instances exist in their environment and verify patching or compensating controls.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Friday added a high-severity security flaw impacting UnrealIRCd, an open-source Internet Relay Chat &#40;IRC&#41; server, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, following reports of active exploitation.” [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### AMD SEV-SNP-protected virtual machines exposed to malicious host data theft

**Review priority:** High · Data protection · Owner: Data and privacy owners

**Why it matters:** The attacks undermine confidential computing assurances for cloud-hosted VMs, allowing host-level access to encrypted memory. Data protection owners should assess reliance on AMD SEV-SNP and verify compensating controls with cloud providers.

**Source evidence:** “Two attacks made public this week allow a malicious host to read data inside AMD SEV-SNP-protected virtual machines &#40;VMs&#41;, which are built to keep the server's operator out. One of them, Mior, can also modify a VM's memory and fake the signed report confirming which software it runs.” [New Mior and Skyfall Attacks Let Rogue Cloud Hosts Steal Secrets From AMD SEV-SNP VMs](https://thehackernews.com/2026/11/new-mior-and-skyfall-attacks-let-rogue.html)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### Check Point Security Gateway targeted by PHP2Shell attacks deploying VMware ESXi wiper

**Review priority:** High · Monitoring and detection · Owner: Detection and monitoring owner

**Why it matters:** The exploitation of gateway appliances to deploy destructive malware on hypervisors indicates a detection gap for lateral movement. Monitoring owners should verify telemetry coverage for Check Point appliances and ESXi host anomalies.

**Source evidence:** “Vulnerable Check Point Security Gateway instances have been targeted in PHP2Shell attacks that deployed data-wiping malware on VMware ESXi hosts…” [Check Point gateways hacked via PHP2Shell to deploy VMware ESXi wiper](https://www.bleepingcomputer.com/news/security/check-point-gateways-hacked-via-php2shell-to-deploy-vmware-esxi-wiper/)

**Evidence to request:** Log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

**Reference controls:** ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)

### Claude Code extension distributed via compromised Cursor marketplace

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** The supply chain compromise through a third-party AI provider highlights risks in marketplace integrity and credential management. Supplier risk owners should review dependencies on Cursor and Fireworks AI and request assurance of remediation.

**Source evidence:** “Cursor confirmed it suffered a security breach that let hackers distribute a malicious Claude Code extension through its marketplace after stealing credentials from AI infrastructure provider Fireworks AI…” [Cursor confirms security breach led to malicious Claude Code extension](https://www.bleepingcomputer.com/news/security/cursor-confirms-security-breach-led-to-malicious-claude-code-extension/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### AI agent manipulated to change vendor bank details via malicious email

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** The demonstration shows AI agents can bypass traditional controls to alter financial transactions, expanding the identity and access attack surface. Access management owners should review AI agent permissions and implement behavioral monitoring for anomalous actions.

**Source evidence:** “An AI agent built to automate invoice processing could be manipulated into changing vendor bank details through a malicious email, without triggering traditional security alerts. Token Security examines five critical AI agent security gaps and shares practical guidance from industry security leaders on preventing them…” [How one AI agent exposed five critical enterprise security gaps](https://www.bleepingcomputer.com/news/security/how-one-ai-agent-exposed-five-critical-enterprise-security-gaps/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### Quantum Systems detects cyberattack disrupting German military drone operations

**Review priority:** High · Incident response · Owner: Incident response lead

**Why it matters:** The confirmed intrusion into a defense contractor highlights the need for robust incident response in critical infrastructure supply chains. Incident response owners should validate containment procedures and evidence retention for supplier-linked attacks.

**Source evidence:** “German defense technology company Quantum Systems confirmed that it detected an incident in late October that was part of an active cyberattack by "hostile actors."…” [German military drone operations disrupted by cyberattack](https://www.bleepingcomputer.com/news/security/german-military-drone-operations-disrupted-by-cyberattack/)

**Evidence to request:** Containment responsibilities, retained logs and the most recent response exercise.

**Decision trigger:** If an exercise exposes an ownership or evidence gap, assign a response-plan correction and retest it.

**Reference controls:** ISO/IEC 27001:2022 A.5.24 (incident management planning and preparation), A.5.26 (response to information security incidents); NIST CSF 2.0 RS.MA (incident management), RS.MI (incident mitigation)

## Source Highlights

- [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-e577b898eca3)
- [PostgreSQL Patches 52 Flaws, Including 22-Year-Old Bug Enabling Authenticated RCE](https://thehackernews.com/2026/11/postgresql-patches-52-flaws-including.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-d8cc2172e29e)
- [Cursor confirms security breach led to malicious Claude Code extension](https://www.bleepingcomputer.com/news/security/cursor-confirms-security-breach-led-to-malicious-claude-code-extension/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-2396f465be93)
- [US disrupts North Korean campaign behind $400 million crypto theft](https://www.bleepingcomputer.com/news/security/us-disrupts-north-korean-campaign-behind-400-million-crypto-theft/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-0eb645ca70f5)
- [ArcticRAT Cybercrime Gang Profiles Victim Finances With AI](https://www.darkreading.com/mobile-security/arcticrat-cybercrime-gang-profiles-victim-finances-ai) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-c281bea158b9)
- [Trezor confirms crypto-stealing implants in three wallets, releases fix](https://www.bleepingcomputer.com/news/cryptocurrency/trezor-confirms-crypto-stealing-implants-in-three-wallets-releases-fix/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-d2962957f52f)
- [German military drone operations disrupted by cyberattack](https://www.bleepingcomputer.com/news/security/german-military-drone-operations-disrupted-by-cyberattack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-6ce23a8d3c69)
- [Check Point gateways hacked via PHP2Shell to deploy VMware ESXi wiper](https://www.bleepingcomputer.com/news/security/check-point-gateways-hacked-via-php2shell-to-deploy-vmware-esxi-wiper/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-97c01e9fc463)
- [New Mior and Skyfall Attacks Let Rogue Cloud Hosts Steal Secrets From AMD SEV-SNP VMs](https://thehackernews.com/2026/11/new-mior-and-skyfall-attacks-let-rogue.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-d93f5e12f3c1)
- [How one AI agent exposed five critical enterprise security gaps](https://www.bleepingcomputer.com/news/security/how-one-ai-agent-exposed-five-critical-enterprise-security-gaps/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-b32ccd39bcb9)
- [FBI Says North Korean Hackers Stole Over $400 Million in Crypto Using Deepfake Video Calls](https://thehackernews.com/2026/11/fbi-says-north-korean-hackers-stole.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-d32b5f97fc67)
- [Trezor Confirms Hidden Implants in CryptoBilis-Sold Wallets That Can Steal Recovery Phrases](https://thehackernews.com/2026/11/trezor-confirms-hidden-hardware.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-14/#reporting-ea8f2c682142)
