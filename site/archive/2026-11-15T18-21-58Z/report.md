# GRC Intelligence Report - 2026-11-15
**Generated:** 2026-11-15T18:21:58.882398Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/0c4e6a1115d2c832ddaf008287b7e66994a65558/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-15](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Italy's €805 million fine against Meta for default-enabled gallery access without explicit consent demonstrates escalating GDPR enforcement on data processing defaults. Simultaneously, TSMC's confirmation that employee personal data was leaked through a cloud provider highlights third-party infrastructure as a direct path for sensitive data exposure. These developments require control owners to validate that default data access settings require documented consent and that cloud supplier contracts include enforceable breach notification and data protection obligations. [Italy Fines Meta €805 Million Over Facebook's Android Gallery Access Without Explicit Consent](https://thehackernews.com/2026/11/italy-fines-meta-805-million-over.html); [TSMC employee data breach linked to cloud provider](https://www.bleepingcomputer.com/news/security/tsmc-employee-data-breach-linked-to-cloud-provider/)

CISA's addition of the UnrealIRCd flaw to the Known Exploited Vulnerabilities catalog and PostgreSQL's patching of 52 flaws including a 22-year-old authenticated RCE vulnerability signal active exploitation of widely deployed infrastructure components. The Cursor marketplace compromise via a stolen Fireworks AI access key and the targeting of Check Point Security Gateways to deploy ESXi wipers demonstrate that supplier credentials and network security appliances are active attack vectors. Control owners must confirm emergency patching for KEV-listed vulnerabilities, extension rebuilding for PostgreSQL, least-privilege scoping of third-party access keys, and integrity monitoring for security gateway and hypervisor layers. [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html); [PostgreSQL Patches 52 Flaws, Including 22-Year-Old Bug Enabling Authenticated RCE](https://thehackernews.com/2026/11/postgresql-patches-52-flaws-including.html); [Check Point gateways hacked via PHP2Shell to deploy VMware ESXi wiper](https://www.bleepingcomputer.com/news/security/check-point-gateways-hacked-via-php2shell-to-deploy-vmware-esxi-wiper/)

Scope: 5 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Facebook for Android feature accesses photos without explicit consent

**Review priority:** High · Data protection · Owner: Data and privacy owners

**Why it matters:** This finding matters for control assurance because it demonstrates regulatory enforcement against default-enabled data access without consent. The accountable owner should confirm that default settings for data access features require explicit user consent and that consent mechanisms are auditable.

**Source evidence:** “Meta was fined €805 million in Italy yesterday over a Facebook for Android feature that suggests photos and videos from users' phone galleries for them to post. The Garante, Italy's data protection authority, found that the feature was enabled by default and that the app accessed Italian users' photos, videos, and related metadata without their explicit consent. The company has 60 days to…” [Italy Fines Meta €805 Million Over Facebook's Android Gallery Access Without Explicit Consent](https://thehackernews.com/2026/11/italy-fines-meta-805-million-over.html)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### cloud provider exposes TSMC employee personal data

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** This finding matters for control assurance because it shows supplier infrastructure compromise leading to sensitive data exposure. The accountable owner should confirm that cloud provider contracts include breach notification obligations and that supplier access to employee data is monitored and minimized.

**Source evidence:** “Taiwan Semiconductor Manufacturing Company &#40;TSMC&#41; confirmed that personal employee data has been leaked online after a threat actor put 6.9GB of information allegedly stolen from the company up for auction…” [TSMC employee data breach linked to cloud provider](https://www.bleepingcomputer.com/news/security/tsmc-employee-data-breach-linked-to-cloud-provider/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### UnrealIRCd added to CISA Known Exploited Vulnerabilities catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** This finding matters for control assurance because CISA KEV inclusion mandates urgent remediation for federal agencies and signals active exploitation. The accountable owner should confirm whether UnrealIRCd is deployed in the environment and that emergency patching procedures have been triggered.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Friday added a high-severity security flaw impacting UnrealIRCd, an open-source Internet Relay Chat &#40;IRC&#41; server, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, following reports of active exploitation. The vulnerability, tracked as CVE-2026-114713 &#40;CVSS score: 8.6&#41;, is a case of improper neutralization of delimiters…” [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### PostgreSQL patches 52 flaws including authenticated RCE vulnerability

**Review priority:** Medium · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** This finding matters for control assurance because the vulnerability allows authenticated remote code execution and requires extension rebuilding for full protection. The accountable owner should confirm that all PostgreSQL instances are patched and that C-language extensions have been rebuilt to eliminate residual exposure.

**Source evidence:** “A type confusion flaw in PostgreSQL lets a database user who can create objects run code on the server. Updates released yesterday fix it, along with 51 other security flaws. Full protection from this flaw also requires rebuilding any C-language extensions installed on the server. The flaw, tracked as CVE-2026-6460, has a CVSS score of 8.8. Any code run this way has the rights of the operating…” [PostgreSQL Patches 52 Flaws, Including 22-Year-Old Bug Enabling Authenticated RCE](https://thehackernews.com/2026/11/postgresql-patches-52-flaws-including.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Check Point Security Gateway instances face PHP2Shell attacks deploying wipers

**Review priority:** Medium · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** This finding matters for control assurance because network security gateways are being exploited to deploy destructive malware on hypervisors. The accountable owner should confirm that Check Point gateways are patched against PHP2Shell exploitation and that ESXi host integrity monitoring detects unauthorized wiper activity.

**Source evidence:** “Vulnerable Check Point Security Gateway instances have been targeted in PHP2Shell attacks that deployed data-wiping malware on VMware ESXi hosts…” [Check Point gateways hacked via PHP2Shell to deploy VMware ESXi wiper](https://www.bleepingcomputer.com/news/security/check-point-gateways-hacked-via-php2shell-to-deploy-vmware-esxi-wiper/)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

## Source Highlights

- [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-e577b898eca3)
- [PostgreSQL Patches 52 Flaws, Including 22-Year-Old Bug Enabling Authenticated RCE](https://thehackernews.com/2026/11/postgresql-patches-52-flaws-including.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d8cc2172e29e)
- [TSMC employee data breach linked to cloud provider](https://www.bleepingcomputer.com/news/security/tsmc-employee-data-breach-linked-to-cloud-provider/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-288ae0a72da3)
- [Italy Fines Meta €805 Million Over Facebook's Android Gallery Access Without Explicit Consent](https://thehackernews.com/2026/11/italy-fines-meta-805-million-over.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-dabf7b9c559f)
- [Cursor Says Stolen Fireworks AI Key Led to Trojanized Claude Code Extension Incident](https://thehackernews.com/2026/11/stolen-fireworks-ai-key-led-to-cursor.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d5585df40181)
- [Cursor confirms security breach led to malicious Claude Code extension](https://www.bleepingcomputer.com/news/security/cursor-confirms-security-breach-led-to-malicious-claude-code-extension/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-2396f465be93)
- [US disrupts North Korean campaign behind $400 million crypto theft](https://www.bleepingcomputer.com/news/security/us-disrupts-north-korean-campaign-behind-400-million-crypto-theft/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-0eb645ca70f5)
- [ArcticRAT Cybercrime Gang Profiles Victim Finances With AI](https://www.darkreading.com/mobile-security/arcticrat-cybercrime-gang-profiles-victim-finances-ai) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-c281bea158b9)
- [Trezor confirms crypto-stealing implants in three wallets, releases fix](https://www.bleepingcomputer.com/news/cryptocurrency/trezor-confirms-crypto-stealing-implants-in-three-wallets-releases-fix/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d2962957f52f)
- [German military drone operations disrupted by cyberattack](https://www.bleepingcomputer.com/news/security/german-military-drone-operations-disrupted-by-cyberattack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-6ce23a8d3c69)
- [Check Point gateways hacked via PHP2Shell to deploy VMware ESXi wiper](https://www.bleepingcomputer.com/news/security/check-point-gateways-hacked-via-php2shell-to-deploy-vmware-esxi-wiper/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-97c01e9fc463)
- [New Mior and Skyfall Attacks Let Rogue Cloud Hosts Steal Secrets From AMD SEV-SNP VMs](https://thehackernews.com/2026/11/new-mior-and-skyfall-attacks-let-rogue.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d93f5e12f3c1)
