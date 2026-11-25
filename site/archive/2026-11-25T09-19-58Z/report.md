# GRC Intelligence Report - 2026-11-25
**Generated:** 2026-11-25T09:19:58.996688Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/f5fdb4460076ddfe32055586d8979c66faebdd43/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-25](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Critical authentication bypass in VMware vCenter and active exploitation of N-able MailAssure and Check Point management servers demand immediate vulnerability management attention. Broadcom has released patches for 23 VMware vulnerabilities including a 9.8-rated auth bypass, while CISA added MailAssure SSRF to its exploited catalog. An AI-driven campaign compromised 24 Check Point management servers across financial services, energy, and government sectors. Vulnerability and monitoring owners should prioritize asset identification, patch validation, and detection coverage for security management interfaces. [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html); [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html); [Hackers Compromise 24 Check Point Management Servers in Suspected AI-Driven Attack Campaign](https://thehackernews.com/2026/11/hackers-compromise-24-check-point.html)

Vishing campaigns hijacking cloud accounts, backdoored WordPress plugins, and the Rackspace Spot platform shutdown reveal expanding identity and supply chain exposures. Com-affiliated actors have conducted vishing against financial services, healthcare, and legal sectors since August 2026. WordPress removed six WP Connect plugins backdoored for arbitrary code execution. Rackspace customers must migrate from Spot by December 8 after Kubernetes cluster and secrets access. Access management and third-party risk owners should verify cloud authentication controls, inventory affected plugins, and assess provider dependencies. [Com-Affiliated Hackers Hijack Cloud Accounts via Vishing for Data Theft and Extortion](https://thehackernews.com/2026/11/com-affiliated-hackers-hijack-cloud.html); [WordPress Blocks Six Backdoored WP Connect Plugins Before Malicious Releases Go Live](https://thehackernews.com/2026/11/wordpress-blocks-six-backdoored-wp.html); [Rackspace shuts down Spot cloud platform after security breach](https://www.bleepingcomputer.com/news/security/rackspace-shuts-down-spot-cloud-platform-after-security-breach/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### VMware vCenter exposes authentication bypass

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** This critical authentication bypass in VMware vCenter weakens access controls for virtualized infrastructure. Vulnerability owners should confirm affected versions are identified and patches applied or compensating controls validated.

**Source evidence:** “Broadcom has shipped patches to address 23 vulnerabilities impacting VMware ESX, vCenter, Workstation, Fusion, and Avi Load Balancer, including one critical bug that could be abused to bypass authentication. The critical vulnerability, tracked as CVE-2026-123903, is rated 9.8 out of 10.0 on the CVSS scoring system. It resides in the VMware Directory Service &#40;"vmdir"&#41;.” [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### N-able MailAssure appears in CISA exploited catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of N-able MailAssure SSRF vulnerability demands immediate asset identification. Vulnerability owners should verify whether MailAssure instances exist in the environment and confirm remediation status.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Monday added two flaws impacting N-able MailAssure and MONAI Label to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing evidence of active exploitation. The critical vulnerabilities are listed below - CVE-2026-134624 &#40;CVSS score: 9.3&#41; - A server-side request forgery &#40;SSRF&#41; vulnerability in N-able MailAssure's LDAP” [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Check Point Security Management servers targeted by AI campaign

**Review priority:** High · Monitoring and detection · Owner: Detection and monitoring owner

**Why it matters:** AI-driven targeting of security management infrastructure challenges detection assumptions. Monitoring owners should review telemetry coverage for Check Point management interfaces and validate alert routing for anomalous administrative activity.

**Source evidence:** “An unknown threat actor has been using artificial intelligence &#40;AI&#41;-driven offensive tooling in a campaign targeting Check Point Security Management servers, impacting 22 distinct organizations across the world. The intrusion activity, tracked by GreyNoise under the moniker GreyNoise Threat 13 &#40;GT13&#41;, is assessed to have targeted organizations in the financial services, energy, government” [Hackers Compromise 24 Check Point Management Servers in Suspected AI-Driven Attack Campaign](https://thehackernews.com/2026/11/hackers-compromise-24-check-point.html)

**Evidence to request:** Log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

**Reference controls:** ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)

### Cloud accounts hijacked via vishing campaigns

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** Vishing campaigns bypassing authentication to hijack cloud accounts expose gaps in identity verification. Access management owners should confirm multi-factor authentication coverage for cloud administrative access and review session revocation procedures.

**Source evidence:** “Palo Alto Networks Unit 42 has disclosed that it's tracking and has responded to "numerous waves of vishing attacks" orchestrated by Com-affiliated threat actors since August 2026 that have led to data theft and extortion attempts. The attacks have targeted financial services, healthcare, and legal services located in the U.S., the U.K., and Australia.” [Com-Affiliated Hackers Hijack Cloud Accounts via Vishing for Data Theft and Extortion](https://thehackernews.com/2026/11/com-affiliated-hackers-hijack-cloud.html)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### WP Connect plugins backdoored in supply chain compromise

**Review priority:** Medium · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Supply chain compromise of WordPress plugins introduces arbitrary code execution risk. Third-party risk owners should inventory WP Connect plugin usage and verify removal or mitigation with application owners.

**Source evidence:** “WordPress has removed six WordPress plugins developed by WP Connect after they were backdoored on November 22, 2026, to enable arbitrary code execution on sites that have them installed, following a suspected compromise of the developer's account. The WordPress plugins team has independently detected and blocked the threat before it could be officially released.” [WordPress Blocks Six Backdoored WP Connect Plugins Before Malicious Releases Go Live](https://thehackernews.com/2026/11/wordpress-blocks-six-backdoored-wp.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Rackspace Spot cloud platform shut down after breach

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Cloud provider breach exposing Kubernetes clusters and secrets forces customer migration. Third-party risk owners should assess dependency on Rackspace Spot, confirm data retrieval, and evaluate alternative provider assurances.

**Source evidence:** “Rackspace is shutting down its Rackspace Spot cloud platform after a security breach allowed hackers to access customer Kubernetes clusters and secrets, giving customers until December 8 to migrate their services and download their data” [Rackspace shuts down Spot cloud platform after security breach](https://www.bleepingcomputer.com/news/security/rackspace-shuts-down-spot-cloud-platform-after-security-breach/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

## Source Highlights

- [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-aa014f4b55f4)
- [Google Researcher Shows How a Single Bit Change in .NET Files Bypassed Windows Code Integrity](https://thehackernews.com/2026/11/google-researcher-shows-how-single-bit.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-372382395c6e)
- [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-d70285cdacc0)
- [Cyber Insurers See New Divide: AI Defense 'Haves' & 'Have Nots'](https://www.darkreading.com/cybersecurity-operations/cyber-insurers-see-new-ai-divide) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-45ee7c2e482d)
- [Microsoft confirms authentication issues after November updates](https://www.bleepingcomputer.com/news/microsoft/microsoft-confirms-authentication-issues-after-november-updates/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-29df4a0d48be)
- [Hackers reportedly breached CIA intelligence analysis system](https://www.bleepingcomputer.com/news/security/hackers-reportedly-breached-cia-intelligence-analysis-system/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-0fe0d4f016d0)
- [Hackers Compromise 24 Check Point Management Servers in Suspected AI-Driven Attack Campaign](https://thehackernews.com/2026/11/hackers-compromise-24-check-point.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-d5f3ce6a4d9a)
- [Com-Affiliated Hackers Hijack Cloud Accounts via Vishing for Data Theft and Extortion](https://thehackernews.com/2026/11/com-affiliated-hackers-hijack-cloud.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-da2703c97fc2)
- [WordPress Blocks Six Backdoored WP Connect Plugins Before Malicious Releases Go Live](https://thehackernews.com/2026/11/wordpress-blocks-six-backdoored-wp.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-da78c9293f40)
- [Satellites Have a Ground-Level Cybersecurity Problem](https://www.darkreading.com/cyber-risk/satellites-ground-level-cybersecurity-problem) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-1b2736ce0451)
- [Webworm APT Slithers Into Networks With Customized SoftEther VPN](https://www.darkreading.com/perimeter/webworm-slithers-customized-softether-vpn) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-c83402675689)
- [Rackspace shuts down Spot cloud platform after security breach](https://www.bleepingcomputer.com/news/security/rackspace-shuts-down-spot-cloud-platform-after-security-breach/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-2b855346dd50)
