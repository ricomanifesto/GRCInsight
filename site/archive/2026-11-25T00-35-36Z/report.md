# GRC Intelligence Report - 2026-11-25
**Generated:** 2026-11-25T00:35:36.623023Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/af44a86bd52d3564d5f87b32da8aca4c0d517d33/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-25](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Multiple critical vulnerabilities with confirmed active exploitation and two major cloud provider breaches demand immediate vendor risk review and patching. Broadcom released patches for 23 VMware flaws including a 9.8-rated authentication bypass in vCenter Directory Service, while CISA added N-able MailAssure and MONAI Label flaws to its Known Exploited Vulnerabilities catalog. Simultaneously, Rackspace shut down its Spot platform after attackers accessed customer Kubernetes clusters and secrets, and Radware exposed customer cloud access keys via an unsecured management API, creating cascading supply chain risk. [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html); [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html); [Rackspace shuts down Spot cloud platform after security breach](https://www.bleepingcomputer.com/news/security/rackspace-shuts-down-spot-cloud-platform-after-security-breach/); [Radware discloses breach exposing customer cloud access keys](https://www.bleepingcomputer.com/news/security/radware-discloses-breach-exposing-customer-cloud-access-keys/)

Identity-targeted campaigns and novel evasion techniques challenge existing detection and authentication controls. The Inception extortion group conducts large-scale vishing against single sign-on credentials across global brands, while the Iran-aligned Volant Manticore group deploys an IPFS-based KuboShell backdoor against telecommunications and critical infrastructure in Cyprus. These developments require identity owners to enforce phishing-resistant MFA and monitoring teams to validate coverage for decentralized command-and-control channels. [New Inception extortion gang launches large-scale vishing campaign](https://www.bleepingcomputer.com/news/security/new-inception-extortion-gang-launches-large-scale-vishing-campaign/); [Iran-Aligned Volant Manticore Uses IPFS-Based KuboShell Backdoor in Espionage Campaigns](https://thehackernews.com/2026/11/iran-aligned-volant-manticore-uses-ipfs.html)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### VMware vCenter Server weakens authentication controls

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** The critical authentication bypass in VMware Directory Service undermines identity verification for virtualized infrastructure. Vulnerability and asset owners should confirm patch deployment across all affected ESX, vCenter, Workstation, Fusion, and Avi Load Balancer instances and verify compensating controls where patching is delayed.

**Source evidence:** “Broadcom has shipped patches to address 23 vulnerabilities impacting VMware ESX, vCenter, Workstation, Fusion, and Avi Load Balancer, including one critical bug that could be abused to bypass authentication. The critical vulnerability, tracked as CVE-2026-123903, is rated 9.8 out of 10.0 on the CVSS scoring system. It resides in the VMware Directory Service &#40;"vmdir"&#41;.” [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### N-able MailAssure LDAP exposes server-side request forgery

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** CISA confirmation of active exploitation for N-able MailAssure and MONAI Label flaws requires immediate asset identification and remediation. Vulnerability and asset owners should verify whether deployed instances are affected and apply vendor patches or implement network segmentation to limit SSRF exposure.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Monday added two flaws impacting N-able MailAssure and MONAI Label to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing evidence of active exploitation. The critical vulnerabilities are listed below - CVE-2026-134624 &#40;CVSS score: 9.3&#41; - A server-side request forgery &#40;SSRF&#41; vulnerability in N-able MailAssure's LDAP” [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Rackspace Spot cloud platform terminates after breach

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** The platform shutdown following unauthorized access to Kubernetes clusters and secrets disrupts service continuity and raises data custody concerns. Supplier risk owners should confirm migration completion, validate data integrity, and assess whether other Rackspace services share similar control gaps.

**Source evidence:** “Rackspace is shutting down its Rackspace Spot cloud platform after a security breach allowed hackers to access customer Kubernetes clusters and secrets, giving customers until December 8 to migrate their services and download their data” [Rackspace shuts down Spot cloud platform after security breach](https://www.bleepingcomputer.com/news/security/rackspace-shuts-down-spot-cloud-platform-after-security-breach/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Radware Cloud WAF management API exposes cloud access keys

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Exposure of customer cloud access keys via an unsecured management API indicates a critical configuration failure in a security vendor's infrastructure. Supplier risk owners should verify key rotation, assess downstream access impact, and demand evidence of API security hardening from Radware.

**Source evidence:** “Cybersecurity company Radware says attackers gained access to some of its customers' account details and cloud access keys through an unsecured internal Cloud WAF &#40;Web Application Firewall&#41; management API that was left exposed online” [Radware discloses breach exposing customer cloud access keys](https://www.bleepingcomputer.com/news/security/radware-discloses-breach-exposing-customer-cloud-access-keys/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Inception extortion gang targets single sign-on credentials

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** A large-scale vishing campaign targeting SSO credentials threatens identity federation across multiple organizations. Identity and access owners should review SSO authentication policies, enforce phishing-resistant MFA, and verify that credential compromise detection covers social engineering vectors.

**Source evidence:** “A newly formed data extortion group named 'Inception' has been linked to a large-scale campaign that targets single sign-on &#40;SSO&#41; credentials of multiple global brands and firms” [New Inception extortion gang launches large-scale vishing campaign](https://www.bleepingcomputer.com/news/security/new-inception-extortion-gang-launches-large-scale-vishing-campaign/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### Volant Manticore KuboShell backdoor uses IPFS for command

**Review priority:** Medium · Monitoring and detection · Owner: Detection and monitoring owner

**Why it matters:** IPFS-based command and control evades traditional network monitoring and targets telecommunications infrastructure. Detection and monitoring owners should evaluate whether current telemetry can identify IPFS traffic patterns and confirm coverage for post-compromise frameworks like Homa in critical sectors.

**Source evidence:** “A previously undocumented Iran-aligned cyber espionage group called Volant Manticore has targeted telecommunications companies, airlines, and critical infrastructure in Cyprus. Central to the group's operations is a backdoor called KuboShell that uses the InterPlanetary File System &#40;IPFS&#41; for command-and-control &#40;C2&#41; and deploys Homa, a post-compromise framework” [Iran-Aligned Volant Manticore Uses IPFS-Based KuboShell Backdoor in Espionage Campaigns](https://thehackernews.com/2026/11/iran-aligned-volant-manticore-uses-ipfs.html)

**Evidence to request:** Log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

**Reference controls:** ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)

## Source Highlights

- [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-aa014f4b55f4)
- [Google Researcher Shows How a Single Bit Change in .NET Files Bypassed Windows Code Integrity](https://thehackernews.com/2026/11/google-researcher-shows-how-single-bit.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-372382395c6e)
- [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-d70285cdacc0)
- [Satellites Have a Ground-Level Cybersecurity Problem](https://www.darkreading.com/cyber-risk/satellites-ground-level-cybersecurity-problem) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-1b2736ce0451)
- [Webworm APT Slithers Into Networks With Customized SoftEther VPN](https://www.darkreading.com/perimeter/webworm-slithers-customized-softether-vpn) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-c83402675689)
- [Rackspace shuts down Spot cloud platform after security breach](https://www.bleepingcomputer.com/news/security/rackspace-shuts-down-spot-cloud-platform-after-security-breach/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-2b855346dd50)
- ['God Mode' Flaws Could Wreak Border-Control Havoc](https://www.darkreading.com/vulnerabilities-threats/god-mode-flaws-wreak-border-control-havoc) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-716dc2a9a70d)
- [New Inception extortion gang launches large-scale vishing campaign](https://www.bleepingcomputer.com/news/security/new-inception-extortion-gang-launches-large-scale-vishing-campaign/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-347042e7abf2)
- [Turnitin discloses cyberattack affecting customer-facing systems](https://www.bleepingcomputer.com/news/security/turnitin-discloses-cyberattack-affecting-customer-facing-systems/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-6c5bc98dced3)
- [Radware discloses breach exposing customer cloud access keys](https://www.bleepingcomputer.com/news/security/radware-discloses-breach-exposing-customer-cloud-access-keys/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-a251bdbac4c3)
- [Iran-Aligned Volant Manticore Uses IPFS-Based KuboShell Backdoor in Espionage Campaigns](https://thehackernews.com/2026/11/iran-aligned-volant-manticore-uses-ipfs.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-9582e29a3fdc)
- [ShinyHunters claims to return after FBI arrests, uses old PGP keys as proof](https://www.bleepingcomputer.com/news/security/shinyhunters-resurfaces-after-fbi-arrests-uses-old-pgp-keys-as-proof/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-25/#reporting-9078000bd51b)
