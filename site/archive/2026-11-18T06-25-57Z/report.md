# GRC Intelligence Report - 2026-11-18
**Generated:** 2026-11-18T06:25:57.770154Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/ffdace038df660a9060e952c0c1826815ba9b9de/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-18](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

A critical Java vulnerability dubbed Java4Shell enables unauthenticated remote code execution in widely deployed enterprise applications including Jira, Jenkins, and Keycloak running on Java 17.0.6 or later with specific hardware capabilities, requiring immediate asset identification and remediation verification by vulnerability management owners. [Java4Shell \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak on Java 17+ AVX-512 VBMI Servers](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)

Multiple third-party incidents — Optimizely serving malware to 178 major websites, Cold Relic weaponizing stolen Google Workspace data for linked intrusions, a compromised Fireworks key accessing Cursor credentials, and Hugging Face lacking ownership verification for AI models — alongside Docker Hub secrets exploited within seconds of publication, collectively indicate systemic gaps in supplier assurance, identity verification, and secret management controls. [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html); [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/); [Cloud keys leaked in Docker Hub images are stolen within seconds](https://www.bleepingcomputer.com/news/security/cloud-keys-leaked-in-docker-hub-images-are-stolen-within-seconds/); [Cursor Traces Malicious Claude Code Extension to Third-Party Breach](https://www.darkreading.com/application-security/cursor-malicious-claude-code-extension-third-party-breach); [Researchers hijack Hugging Face account for popular Kokoro AI model](https://www.bleepingcomputer.com/news/security/researchers-hijack-hugging-face-account-for-popular-kokoro-ai-model/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Jira, Jenkins, Keycloak expose unauthenticated remote code execution

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** A pre-authentication RCE vulnerability in widely deployed enterprise applications undermines vulnerability management coverage and requires immediate asset identification. The accountable owner should confirm affected-asset inventory, installed versions, and remediation status with exception ownership.

**Source evidence:** “A Java flaw called Java4Shell can let attackers without an account run their own code on Jira, Jenkins, Keycloak, and three other widely used applications, says Calif, the security research firm that disclosed it this week. The flaw is present in Java 17.0.6 and later, and the vulnerable code runs only on x86-64 Intel and AMD chips that support the AVX-512 VBMI feature. Tracked as…” [Java4Shell \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak on Java 17+ AVX-512 VBMI Servers](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Cold Relic weaponizes single cloud compromise for linked intrusions

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A single cloud compromise escalating into a chain of third-party intrusions demonstrates how supplier access can amplify blast radius. The supplier risk owner should review relevant supplier dependencies, assurance evidence, and escalation contacts for cloud identity providers.

**Source evidence:** “The Russia-linked cyber espionage group known as Cold Relic &#40;formerly COLDRIVER and UNC4057&#41; has been observed weaponizing a single cloud compromise into a launchpad for a series of linked intrusions resulting in third-party compromise. Google's Mandiant and Threat Intelligence Group &#40;GTIG&#41; said it investigated a 2026 compromise at a U.S.-based organization in which the adversary leveraged…” [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Optimizely injects malware into 178 top websites

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A third-party experience platform compromise silently distributed malware to major brand websites, exposing gaps in content source governance. The supplier risk owner should verify third-party content source controls, supplier assurance evidence, and contractual remediation obligations.

**Source evidence:** “At least 178 top web destinations unwittingly served a variety of malware exploits against visitors over the past 24 hours thanks to a security vulnerability involving Optimizely, a company that helps websites customize user experiences and test out new features. Experts say the incident, which saw data-stealing malicious software silently injected into sites like the BBC, CNN, Equifax, Ledger and Zoom, was exacerbated by the reality that few popular websites enforce strict rules on the sources of third-party content.” [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### public Docker Hub images leak credentials exploited within seconds

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** Secrets embedded in public container images are harvested almost instantly, rendering manual rotation ineffective. The identity and access owner should confirm secret scanning coverage in CI/CD pipelines, automated revocation workflows, and evidence of rotation compliance.

**Source evidence:** “Credentials and access secrets exposed in public Docker Hub images are being extracted and exploited by attackers within as little as eight seconds of publication…” [Cloud keys leaked in Docker Hub images are stolen within seconds](https://www.bleepingcomputer.com/news/security/cloud-keys-leaked-in-docker-hub-images-are-stolen-within-seconds/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### Compromised key issued to Fireworks exposes Cursor data and credentials

**Review priority:** Medium · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A compromised API key at an AI infrastructure provider enabled unauthorized access to customer data and credentials. The supplier risk owner should assess the supplier's key management practices, access scope limitations, and evidence of remediation assurance.

**Source evidence:** “A compromised key issued to AI infrastructure provider Fireworks was used by threat actors to access Cursor data and credentials.” [Cursor Traces Malicious Claude Code Extension to Third-Party Breach](https://www.darkreading.com/application-security/cursor-malicious-claude-code-extension-third-party-breach)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Hugging Face platform lacks ownership verification for AI models

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** Absence of ownership verification on a model hosting platform enabled account takeover of a widely used AI model. The identity and access owner should confirm identity verification controls for model repositories and assess supply chain integrity for AI dependencies.

**Source evidence:** “A Lack of ownership verification on the Hugging Face platform allowed researchers to take control of Kokoro, a text-to-speech model used in projects from Google, NVIDIA, AMD, Intel, and Amazon Web Services…” [Researchers hijack Hugging Face account for popular Kokoro AI model](https://www.bleepingcomputer.com/news/security/researchers-hijack-hugging-face-account-for-popular-kokoro-ai-model/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

## Source Highlights

- [Java4Shell \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak on Java 17+ AVX-512 VBMI Servers](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-5966ac56e61b)
- [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-4816a5c313d5)
- [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-e010dc913600)
- [Critical Java4Shell flaw allows RCE attacks on major Java applications](https://www.bleepingcomputer.com/news/security/critical-java4shell-flaw-allows-rce-attacks-on-major-java-applications/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-fca3dc2fb776)
- [Optimizely Malware Attacks Highlight Third-Party Vendor Risks](https://www.darkreading.com/cyber-risk/optimizely-malware-attacks-third-party-vendor-risks) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-eca290345628)
- [Cloud keys leaked in Docker Hub images are stolen within seconds](https://www.bleepingcomputer.com/news/security/cloud-keys-leaked-in-docker-hub-images-are-stolen-within-seconds/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-2cac7202a964)
- ['TheMailer' Phishing Kit Puts AI in the Driver's Seat](https://www.darkreading.com/perimeter/themailer-phishing-kit-ai-drivers-seat) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-164e150f1026)
- [Japan takes Fugaku supercomputer offlline after cyberattack](https://www.bleepingcomputer.com/news/security/japan-takes-fugaku-supercomputer-offlline-after-cyberattack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-b578b4efad12)
- [Researchers Claim Two RCE Exploits That Bypass Telegram’s New Android Defenses](https://thehackernews.com/2026/11/researchers-claim-two-rce-exploits-that.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-6bab39afba04)
- [Apple reports outages affecting iCloud Mail, AppleCare and more](https://www.bleepingcomputer.com/news/apple/apple-reports-outages-affecting-icloud-mail-applecare-and-more/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-d82820a08fcb)
- [Cursor Traces Malicious Claude Code Extension to Third-Party Breach](https://www.darkreading.com/application-security/cursor-malicious-claude-code-extension-third-party-breach) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-a27a6af66fc8)
- [Researchers hijack Hugging Face account for popular Kokoro AI model](https://www.bleepingcomputer.com/news/security/researchers-hijack-hugging-face-account-for-popular-kokoro-ai-model/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-a5a96cf48fc1)
