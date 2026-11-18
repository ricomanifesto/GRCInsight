# GRC Intelligence Report - 2026-11-18
**Generated:** 2026-11-18T09:19:08.533633Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/d85f028a8743376952db4d130b4c847816e5c205/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-18](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

A critical pre-authentication RCE vulnerability in Java applications including Jira, Jenkins, and Keycloak, combined with an active supply chain compromise of Microsoft's agent-framework package and rapid exploitation of credentials exposed in public Docker Hub images, weakens vulnerability management, third-party risk, and data protection controls across the enterprise. Control owners must verify affected asset inventories, supplier assurance evidence, and secret scanning coverage. [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html); [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html); [Cloud keys leaked in Docker Hub images are stolen within seconds](https://www.bleepingcomputer.com/news/security/cloud-keys-leaked-in-docker-hub-images-are-stolen-within-seconds/)

A Russia-linked threat actor weaponized a cloud compromise for linked intrusions, a third-party platform vulnerability in Optimizely injected malware into 178 major websites, and an AI-driven phishing kit automates personalized credential theft, extending third-party risk and access management exposures. Owners should review cloud compromise containment, supplier control responsibilities, and phishing detection capabilities. [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html); [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/); ['TheMailer' Phishing Kit Puts AI in the Driver's Seat](https://www.darkreading.com/perimeter/themailer-phishing-kit-ai-drivers-seat)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Jira, Jenkins, Keycloak enable pre-auth RCE via Java4Shell flaw

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** The vulnerability allows unauthenticated remote code execution in widely deployed enterprise applications, weakening vulnerability management controls. The vulnerability owner should confirm affected asset inventory and remediation status for Java 17.0.6 and later on x86-64 systems.

**Source evidence:** “A Java flaw called Java4Shell can let attackers without an account run their own code on Jira, Jenkins, Keycloak, and three other widely used applications, says Calif, the security research firm that disclosed it this week. The flaw is present in Java 17.0.6 and later, and the vulnerable code runs only on x86-64 Intel and AMD chips that support the AVX-512 VBMI feature.” [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Microsoft's agent-framework package delivers credential stealer via PyPI compromise

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A legitimate Microsoft package was compromised to distribute a credential stealer, exposing third-party risk in software supply chains. The supplier risk owner should review dependencies on Microsoft's agent-framework and obtain assurance evidence for remediation.

**Source evidence:** “Threat actors have compromised Microsoft's agent-framework package to push a credential stealer, according to reports from Aikido, Chainguard, Endor Labs, OX Security, SafeDep, Socket, StepSecurity, and Google-owned Wiz. The malicious versions, 1.26.1 and 1.26.2, were published 33 minutes apart on November 17, 2026, and are designed to run a credential stealer on every Python start.” [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Credentials and access secrets are extracted and exploited within seconds

**Review priority:** High · Data protection · Owner: Data and privacy owners

**Why it matters:** Cloud credentials in public container images are exploited almost instantly, undermining data protection for secrets management. The data protection owner should verify secret scanning coverage and credential rotation procedures for Docker Hub deployments.

**Source evidence:** “Credentials and access secrets exposed in public Docker Hub images are being extracted and exploited by attackers within as little as eight seconds of publication” [Cloud keys leaked in Docker Hub images are stolen within seconds](https://www.bleepingcomputer.com/news/security/cloud-keys-leaked-in-docker-hub-images-are-stolen-within-seconds/)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### Cold Relic weaponizes cloud compromise for third-party intrusions

**Review priority:** Medium · Data protection · Owner: Data and privacy owners

**Why it matters:** A Russia-linked espionage group used a single cloud compromise to launch further intrusions, weakening data protection controls for cloud environments. The data protection owner should review cloud compromise containment procedures and access restrictions for sensitive data.

**Source evidence:** “The Russia-linked cyber espionage group known as Cold Relic &#40;formerly COLDRIVER and UNC4057&#41; has been observed weaponizing a single cloud compromise into a launchpad for a series of linked intrusions resulting in third-party compromise. Google's Mandiant and Threat Intelligence Group &#40;GTIG&#41; said it investigated a 2026 compromise at a U.S.-based organization in which the adversary leveraged” [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### Optimizely injects malware into 178 top websites via third-party vulnerability

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A third-party platform vulnerability enabled mass malware delivery to visitors of major websites, extending third-party risk exposure. The supplier risk owner should review Optimizely's control responsibilities and the assurance evidence for remediation.

**Source evidence:** “At least 178 top web destinations unwittingly served a variety of malware exploits against visitors over the past 24 hours thanks to a security vulnerability involving Optimizely, a company that helps websites customize user experiences and test out new features. Experts say the incident, which saw data-stealing malicious software silently injected into sites like the BBC, CNN, Equifax, Ledger and Zoom, was exacerbated by the reality that few popular websites enforce strict rules on the sources of third-party content.” [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### The commercial kit uses AI models to personalize lures and evade filters

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** An AI-driven phishing kit automates personalized lure creation and spam filter evasion, challenging access management controls for credential theft. The identity and access owner should confirm phishing detection coverage and authentication resilience against scaled campaigns.

**Source evidence:** “The commercial kit uses attacker-supplied AI models to personalize lures, evade spam filters, and scale campaigns to tens of thousands of targets.” ['TheMailer' Phishing Kit Puts AI in the Driver's Seat](https://www.darkreading.com/perimeter/themailer-phishing-kit-ai-drivers-seat)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

## Source Highlights

- [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-5966ac56e61b)
- [British Scattered Spider hacker sentenced to 6 years in prison](https://www.bleepingcomputer.com/news/security/british-scattered-spider-hacker-sentenced-to-6-years-in-prison/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-9f8e9c27a393)
- [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-533b590042a0)
- [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-4816a5c313d5)
- [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-e010dc913600)
- [Critical Java4Shell flaw allows RCE attacks on major Java applications](https://www.bleepingcomputer.com/news/security/critical-java4shell-flaw-allows-rce-attacks-on-major-java-applications/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-fca3dc2fb776)
- [Optimizely Malware Attacks Highlight Third-Party Vendor Risks](https://www.darkreading.com/cyber-risk/optimizely-malware-attacks-third-party-vendor-risks) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-eca290345628)
- [Cloud keys leaked in Docker Hub images are stolen within seconds](https://www.bleepingcomputer.com/news/security/cloud-keys-leaked-in-docker-hub-images-are-stolen-within-seconds/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-2cac7202a964)
- ['TheMailer' Phishing Kit Puts AI in the Driver's Seat](https://www.darkreading.com/perimeter/themailer-phishing-kit-ai-drivers-seat) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-164e150f1026)
- [Japan takes Fugaku supercomputer offlline after cyberattack](https://www.bleepingcomputer.com/news/security/japan-takes-fugaku-supercomputer-offlline-after-cyberattack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-b578b4efad12)
- [Researchers Claim Two RCE Exploits That Bypass Telegram’s New Android Defenses](https://thehackernews.com/2026/11/researchers-claim-two-rce-exploits-that.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-6bab39afba04)
- [Apple reports outages affecting iCloud Mail, AppleCare and more](https://www.bleepingcomputer.com/news/apple/apple-reports-outages-affecting-icloud-mail-applecare-and-more/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-d82820a08fcb)
