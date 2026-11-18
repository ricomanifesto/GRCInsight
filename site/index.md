# GRC Intelligence Report - 2026-11-18
**Generated:** 2026-11-18T18:20:00.92447Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/8eea43039fd35b004a86c281e900fdcbff8be1c6/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-18](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Critical vulnerabilities in widely used infrastructure software are being actively exploited, with CISA adding a Perforce Puppet flaw to its Known Exploited Vulnerabilities catalog and threat actors exploiting an Apache Roller flaw for code execution. Simultaneously, a supply chain compromise of Microsoft's Agent Framework Python package on PyPI has exposed developer credentials. These developments require vulnerability and asset owners to confirm affected asset inventories and remediation status, and supplier risk owners to review dependencies and assurance evidence for compromised components. [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html)

Identity verification controls are under pressure from deepfake-enabled helpdesk impersonation and fake IT support requests that bypass authentication, while a physical attack can reset TPM lockouts to guess Windows Hello and BitLocker PINs. Additionally, the EggStreme malware toolkit has been rebuilt to evade detection against government targets. Access management and monitoring owners should verify authentication coverage, session revocation evidence, telemetry coverage, and detection test results to address these evolving threats. [New Attack Bypasses TPM Lockout to Crack Windows Hello and BitLocker PINs in Days, Not Years](https://thehackernews.com/2026/11/flash-chip-attack-bypasses-tpm-lockout.html)

Scope: 2 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Perforce Puppet added to CISA KEV catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a critical infrastructure-as-code platform demands immediate vulnerability management. The accountable owner should confirm affected asset inventory and remediation status.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Tuesday added a critical security flaw impacting Perforce Puppet, an enterprise infrastructure-as-code &#40;IaC&#41; and configuration management platform, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing reports of active exploitation.” [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### TPM lockout bypassed via physical access

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** Physical access can defeat TPM-protected authentication. The identity and access owner should confirm authentication coverage and session revocation evidence.

**Source evidence:** “On AMD-based PCs and some Intel PCs, the TPM lockout for Windows Hello and BitLocker PINs can be reset by someone who opens the PC's case, researchers at Technische Universität Berlin say. That leaves short PINs open to guessing. In lab tests, the researchers found a four-digit Hello PIN on an AMD laptop and a 6-digit BitLocker PIN on an Intel laptop this way.” [New Attack Bypasses TPM Lockout to Crack Windows Hello and BitLocker PINs in Days, Not Years](https://thehackernews.com/2026/11/flash-chip-attack-bypasses-tpm-lockout.html)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

## Source Highlights

- [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-5966ac56e61b)
- [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-eeab189c3475)
- [Microsoft’s Agent Framework PyPI package compromised to steal credentials](https://www.bleepingcomputer.com/news/security/microsofts-agent-framework-pypi-package-compromised-to-steal-credentials/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-97ef079b76ea)
- [Java4Shell Flaw Threatens Global Enterprises, Java Application Ecosystem](https://www.darkreading.com/vulnerabilities-threats/java4shell-flaw-threatens-global-java-application-ecosystem) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-b614b4646977)
- [From Deepfakes to Helpdesk Impersonation: Why Stronger Verification Matters](https://www.bleepingcomputer.com/news/security/from-deepfakes-to-helpdesk-impersonation-why-stronger-verification-matters/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-993f9d718221)
- [New EggStreme Malware Variant Goes Silent to Evade Security Tools in Government Attacks](https://thehackernews.com/2026/11/eggstreme-hackers-rebuild-malware-with.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-16d1e418da7e)
- [Major Brazilian Signature Apps Enable RCE & Fraud](https://www.darkreading.com/vulnerabilities-threats/major-brazilian-signature-app-rce-fraud) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-4a99733142bf)
- [New Attack Bypasses TPM Lockout to Crack Windows Hello and BitLocker PINs in Days, Not Years](https://thehackernews.com/2026/11/flash-chip-attack-bypasses-tpm-lockout.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-90f84e48047f)
- [AI Pentesting Checklist for Web Apps: 15 Questions to Ask Before Choosing a Vendor](https://thehackernews.com/2026/11/ai-pentesting-checklist-for-web-apps-15.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-e3f6e444c8de)
- [Dizigom illegal streaming service with 21M monthly visits shuts down](https://www.bleepingcomputer.com/news/security/dizigom-illegal-streaming-service-with-21m-monthly-visits-shuts-down/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-75d2be14123c)
- [Quality Isn’t The Main Worry About AI Pentesting — Data Privacy and Production Safety Are](https://thehackernews.com/2026/11/quality-isnt-main-worry-about-ai.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-1df2f3726abc)
- [Apache warns of Roller RCE vulnerability exploited in attacks](https://www.bleepingcomputer.com/news/security/apache-warns-of-roller-rce-vulnerability-exploited-in-attacks/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-4d4692262fd0)
