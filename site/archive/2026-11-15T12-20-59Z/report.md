# GRC Intelligence Report - 2026-11-15
**Generated:** 2026-11-15T12:20:59.603115Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/58302ca345f316bf7106856e02243bdc25a4eb3b/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-15](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Regulatory enforcement and supply chain compromises dominate this period. Italy's data protection authority fined Meta €805 million for processing user gallery data without explicit consent, signaling stricter consent enforcement for mobile applications. Simultaneously, a stolen access key issued to Fireworks AI enabled malicious code distribution through Cursor's extension marketplace, demonstrating how third-party credentials can compromise trusted software supply chains. These events require data protection owners to validate consent mechanisms and supplier risk owners to review issued credential scopes and marketplace integrity controls. [Italy Fines Meta €805 Million Over Facebook's Android Gallery Access Without Explicit Consent](https://thehackernews.com/2026/11/italy-fines-meta-805-million-over.html)

Active exploitation and emerging attack vectors expand remediation priorities. CISA added an UnrealIRCd vulnerability to its Known Exploited Vulnerabilities catalog, mandating immediate asset identification. New research reveals AMD SEV-SNP confidential VMs can be compromised by malicious hosts with hypervisor and BIOS control, challenging cloud data protection assumptions. An AI invoice processing agent was manipulated to alter vendor payments without triggering alerts, exposing governance gaps in autonomous systems. Hardware supply chain implants in Trezor wallets further demonstrate physical-layer risks. Vulnerability management, data protection, governance, and supplier risk owners should reassess coverage for these vectors. [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html); [New Mior and Skyfall Attacks Let Rogue Cloud Hosts Steal Secrets From AMD SEV-SNP VMs](https://thehackernews.com/2026/11/new-mior-and-skyfall-attacks-let-rogue.html); [How one AI agent exposed five critical enterprise security gaps](https://www.bleepingcomputer.com/news/security/how-one-ai-agent-exposed-five-critical-enterprise-security-gaps/); [Trezor confirms crypto-stealing implants in three wallets, releases fix](https://www.bleepingcomputer.com/news/cryptocurrency/trezor-confirms-crypto-stealing-implants-in-three-wallets-releases-fix/)

Scope: 5 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Facebook for Android feature accesses photos without explicit consent

**Review priority:** High · Data protection · Owner: Data and privacy owners

**Why it matters:** This fine demonstrates regulatory enforcement of consent requirements for mobile data access. Data protection owners should confirm that mobile application data access controls obtain and record explicit user consent before processing gallery content.

**Source evidence:** “Meta was fined €805 million in Italy yesterday over a Facebook for Android feature that suggests photos and videos from users' phone galleries for them to post. The Garante, Italy's data protection authority, found that the feature was enabled by default and that the app accessed Italian users' photos, videos, and related metadata without their explicit consent.” [Italy Fines Meta €805 Million Over Facebook's Android Gallery Access Without Explicit Consent](https://thehackernews.com/2026/11/italy-fines-meta-805-million-over.html)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### UnrealIRCd open-source IRC server added to CISA exploited vulnerabilities catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of this server vulnerability mandates immediate asset identification and remediation. Vulnerability management owners should confirm whether UnrealIRCd instances exist in the environment and that patching or compensating controls are applied.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Friday added a high-severity security flaw impacting UnrealIRCd, an open-source Internet Relay Chat &#40;IRC&#41; server, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, following reports of active exploitation. The vulnerability, tracked as CVE-2026-114713 &#40;CVSS score: 8.6&#41;, is a case of improper neutralization of delimiters” [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### AMD SEV-SNP-protected virtual machines exposed to malicious host attacks

**Review priority:** High · Data protection · Owner: Data and privacy owners

**Why it matters:** Cloud confidential computing protections can be bypassed by privileged host actors. Data protection owners should assess whether workloads relying on SEV-SNP encryption have additional controls for host compromise scenarios and verify attestation verification processes.

**Source evidence:** “Two attacks made public this week allow a malicious host to read data inside AMD SEV-SNP-protected virtual machines &#40;VMs&#41;, which are built to keep the server's operator out. One of them, Mior, can also modify a VM's memory and fake the signed report confirming which software it runs. Both need control of the server's hypervisor, and Mior also needs control of the server's BIOS.” [New Mior and Skyfall Attacks Let Rogue Cloud Hosts Steal Secrets From AMD SEV-SNP VMs](https://thehackernews.com/2026/11/new-mior-and-skyfall-attacks-let-rogue.html)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### AI agent built to automate invoice processing manipulated to change vendor bank details

**Review priority:** Medium · Governance and accountability · Owner: Risk and control owners

**Why it matters:** Autonomous AI agents introduce new attack surfaces that bypass conventional controls. Governance owners should confirm that AI agent deployments have defined ownership, approval workflows, and monitoring for unauthorized actions affecting financial transactions.

**Source evidence:** “An AI agent built to automate invoice processing could be manipulated into changing vendor bank details through a malicious email, without triggering traditional security alerts. Token Security examines five critical AI agent security gaps and shares practical guidance from industry security leaders on preventing them” [How one AI agent exposed five critical enterprise security gaps](https://www.bleepingcomputer.com/news/security/how-one-ai-agent-exposed-five-critical-enterprise-security-gaps/)

**Evidence to request:** The affected assumption, accountable owner and a recorded decision to act or accept risk.

**Decision trigger:** If an assumption no longer holds, record an accountable decision to change the control or accept the resulting uncertainty.

**Reference controls:** ISO/IEC 27001:2022 A.5.1 (policies for information security), A.5.2 (roles and responsibilities); NIST CSF 2.0 GV.RR (roles, responsibilities and authorities), GV.OV (oversight)

### Safe 5 devices sold by Southeast Asian reseller CryptoBilis contain malicious hardware implants

**Review priority:** Medium · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Hardware supply chain compromise enables secret extraction at the physical layer. Supplier risk owners should verify authorized reseller programs, device integrity verification processes, and incident response for compromised hardware distributions.

**Source evidence:** “Cryptocurrency hardware wallet maker Trezor has confirmed that three Safe 5 devices sold by Southeast Asian reseller CryptoBilis contained malicious hardware implants designed to steal wallet recovery phrases and send them to attackers over cellular networks” [Trezor confirms crypto-stealing implants in three wallets, releases fix](https://www.bleepingcomputer.com/news/cryptocurrency/trezor-confirms-crypto-stealing-implants-in-three-wallets-releases-fix/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

## Source Highlights

- [Attackers Exploit UnrealIRCd Flaw That Enables Server-Level Command Injection](https://thehackernews.com/2026/11/attackers-exploit-unrealircd-flaw-that.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-e577b898eca3)
- [PostgreSQL Patches 52 Flaws, Including 22-Year-Old Bug Enabling Authenticated RCE](https://thehackernews.com/2026/11/postgresql-patches-52-flaws-including.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d8cc2172e29e)
- [Italy Fines Meta €805 Million Over Facebook's Android Gallery Access Without Explicit Consent](https://thehackernews.com/2026/11/italy-fines-meta-805-million-over.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-dabf7b9c559f)
- [Cursor Says Stolen Fireworks AI Key Led to Trojanized Claude Code Extension Incident](https://thehackernews.com/2026/11/stolen-fireworks-ai-key-led-to-cursor.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d5585df40181)
- [Cursor confirms security breach led to malicious Claude Code extension](https://www.bleepingcomputer.com/news/security/cursor-confirms-security-breach-led-to-malicious-claude-code-extension/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-2396f465be93)
- [US disrupts North Korean campaign behind $400 million crypto theft](https://www.bleepingcomputer.com/news/security/us-disrupts-north-korean-campaign-behind-400-million-crypto-theft/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-0eb645ca70f5)
- [ArcticRAT Cybercrime Gang Profiles Victim Finances With AI](https://www.darkreading.com/mobile-security/arcticrat-cybercrime-gang-profiles-victim-finances-ai) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-c281bea158b9)
- [Trezor confirms crypto-stealing implants in three wallets, releases fix](https://www.bleepingcomputer.com/news/cryptocurrency/trezor-confirms-crypto-stealing-implants-in-three-wallets-releases-fix/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d2962957f52f)
- [German military drone operations disrupted by cyberattack](https://www.bleepingcomputer.com/news/security/german-military-drone-operations-disrupted-by-cyberattack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-6ce23a8d3c69)
- [Check Point gateways hacked via PHP2Shell to deploy VMware ESXi wiper](https://www.bleepingcomputer.com/news/security/check-point-gateways-hacked-via-php2shell-to-deploy-vmware-esxi-wiper/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-97c01e9fc463)
- [New Mior and Skyfall Attacks Let Rogue Cloud Hosts Steal Secrets From AMD SEV-SNP VMs](https://thehackernews.com/2026/11/new-mior-and-skyfall-attacks-let-rogue.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-d93f5e12f3c1)
- [How one AI agent exposed five critical enterprise security gaps](https://www.bleepingcomputer.com/news/security/how-one-ai-agent-exposed-five-critical-enterprise-security-gaps/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-15/#reporting-b32ccd39bcb9)
