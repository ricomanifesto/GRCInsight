# GRC Intelligence Report - 2026-11-24
**Generated:** 2026-11-24T21:18:34.983281Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/7a8b8d67657eaa80bf4b3a04ee4b382d82db7ecf/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-24](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Critical vulnerabilities in widely deployed infrastructure demand urgent remediation verification. CISA added N-able MailAssure to its Known Exploited Vulnerabilities catalog citing active exploitation, while Broadcom released patches for 23 VMware flaws including a critical authentication bypass in vCenter. Control owners must confirm affected asset inventories and patch deployment status across virtualized and email security platforms. [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html); [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html)

Identity-targeted campaigns and supplier breaches elevate access management and third-party risk. The Inception extortion group targets single sign-on credentials through vishing, Radware exposed customer cloud keys via an unsecured management API, and the EU Academy breach compromised personal data. Meanwhile, Iran-aligned Volant Manticore uses IPFS-based backdoors against telecommunications and critical infrastructure. Owners should validate privileged access controls, supplier assurance evidence, data protection monitoring, and detection coverage for novel command-and-control channels. [New Inception extortion gang launches large-scale vishing campaign](https://www.bleepingcomputer.com/news/security/new-inception-extortion-gang-launches-large-scale-vishing-campaign/); [Radware discloses breach exposing customer cloud access keys](https://www.bleepingcomputer.com/news/security/radware-discloses-breach-exposing-customer-cloud-access-keys/); [European Commission confirms data theft in EU Academy breach](https://www.bleepingcomputer.com/news/security/european-commission-confirms-data-theft-in-eu-academy-breach/); [Iran-Aligned Volant Manticore Uses IPFS-Based KuboShell Backdoor in Espionage Campaigns](https://thehackernews.com/2026/11/iran-aligned-volant-manticore-uses-ipfs.html)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### vCenter weakens authentication assurance

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** The critical authentication bypass in vCenter undermines identity verification controls across virtualized infrastructure. Vulnerability owners must confirm that all affected vCenter instances are inventoried and patched per Broadcom's advisory.

**Source evidence:** “Broadcom has shipped patches to address 23 vulnerabilities impacting VMware ESX, vCenter, Workstation, Fusion, and Avi Load Balancer, including one critical bug that could be abused to bypass authentication. The critical vulnerability, tracked as CVE-2026-123903, is rated 9.8 out of 10.0 on the CVSS scoring system. It resides in the VMware Directory Service &#40;"vmdir"&#41;.” [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### N-able MailAssure extends active exploitation risk

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** CISA's KEV listing confirms active exploitation of an SSRF flaw in N-able MailAssure, requiring immediate remediation verification. Vulnerability owners must confirm whether deployed instances are affected and that patches or mitigations are applied.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Monday added two flaws impacting N-able MailAssure and MONAI Label to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing evidence of active exploitation. The critical vulnerabilities are listed below - CVE-2026-134624 &#40;CVSS score: 9.3&#41; - A server-side request forgery &#40;SSRF&#41; vulnerability in N-able MailAssure's LDAP…” [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### single sign-on &#40;SSO&#41; credentials exposes credential theft risk

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** The Inception group's vishing campaign directly targets SSO credentials, challenging authentication assurance for cloud and federated access. Identity owners should review MFA coverage, session revocation procedures, and user awareness training effectiveness.

**Source evidence:** “A newly formed data extortion group named 'Inception' has been linked to a large-scale campaign that targets single sign-on &#40;SSO&#41; credentials of multiple global brands and firms…” [New Inception extortion gang launches large-scale vishing campaign](https://www.bleepingcomputer.com/news/security/new-inception-extortion-gang-launches-large-scale-vishing-campaign/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### unsecured internal Cloud WAF &#40;Web Application Firewall&#41; management API exposes cloud access keys

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Radware's exposed management API compromised customer cloud access keys, demonstrating a critical supplier control failure. Supplier risk owners must assess Radware's access scope, request assurance of remediation, and review their own cloud key rotation policies.

**Source evidence:** “Cybersecurity company Radware says attackers gained access to some of its customers' account details and cloud access keys through an unsecured internal Cloud WAF &#40;Web Application Firewall&#41; management API that was left exposed online…” [Radware discloses breach exposing customer cloud access keys](https://www.bleepingcomputer.com/news/security/radware-discloses-breach-exposing-customer-cloud-access-keys/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### EU Academy online learning hub exposes personal data theft

**Review priority:** Medium · Data protection · Owner: Data and privacy owners

**Why it matters:** The EU Academy breach resulted in personal data theft, triggering GDPR notification obligations and highlighting platform security gaps. Data protection owners must verify the scope of exposed data, assess notification compliance, and review learning platform security controls.

**Source evidence:** “The European Commission, the European Union's main executive body, has confirmed that attackers breached its EU Academy online learning hub and stole the personal data of an undisclosed number of users…” [European Commission confirms data theft in EU Academy breach](https://www.bleepingcomputer.com/news/security/european-commission-confirms-data-theft-in-eu-academy-breach/)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### KuboShell extends IPFS-based espionage capability

**Review priority:** Medium · Monitoring and detection · Owner: Detection and monitoring owner

**Why it matters:** Volant Manticore's use of IPFS for C2 via KuboShell evades traditional network monitoring, targeting telecommunications and critical infrastructure. Monitoring owners should evaluate detection coverage for IPFS traffic and assess telemetry gaps in critical sectors.

**Source evidence:** “A previously undocumented Iran-aligned cyber espionage group called Volant Manticore has targeted telecommunications companies, airlines, and critical infrastructure in Cyprus. Central to the group's operations is a backdoor called KuboShell that uses the InterPlanetary File System &#40;IPFS&#41; for command-and-control &#40;C2&#41; and deploys Homa, a post-compromise framework that's a reimplementation of…” [Iran-Aligned Volant Manticore Uses IPFS-Based KuboShell Backdoor in Espionage Campaigns](https://thehackernews.com/2026/11/iran-aligned-volant-manticore-uses-ipfs.html)

**Evidence to request:** Log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

**Reference controls:** ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)

## Source Highlights

- [VMware vCenter Hit by Another Critical 9.8-Rated Auth Bypass Flaw After Zero-Day Exploitation](https://thehackernews.com/2026/11/vmware-vcenter-hit-by-another-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-aa014f4b55f4)
- [Google Researcher Shows How a Single Bit Change in .NET Files Bypassed Windows Code Integrity](https://thehackernews.com/2026/11/google-researcher-shows-how-single-bit.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-372382395c6e)
- [Hackers Exploit N-able MailAssure Flaw While AI Agents Exploit MONAI Label Zero-Day](https://thehackernews.com/2026/11/hackers-exploit-n-able-mailassure-flaw.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-d70285cdacc0)
- [New Inception extortion gang launches large-scale vishing campaign](https://www.bleepingcomputer.com/news/security/new-inception-extortion-gang-launches-large-scale-vishing-campaign/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-347042e7abf2)
- [Turnitin discloses cyberattack affecting customer-facing systems](https://www.bleepingcomputer.com/news/security/turnitin-discloses-cyberattack-affecting-customer-facing-systems/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-6c5bc98dced3)
- [Radware discloses breach exposing customer cloud access keys](https://www.bleepingcomputer.com/news/security/radware-discloses-breach-exposing-customer-cloud-access-keys/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-a251bdbac4c3)
- [Iran-Aligned Volant Manticore Uses IPFS-Based KuboShell Backdoor in Espionage Campaigns](https://thehackernews.com/2026/11/iran-aligned-volant-manticore-uses-ipfs.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-9582e29a3fdc)
- [ShinyHunters claims to return after FBI arrests, uses old PGP keys as proof](https://www.bleepingcomputer.com/news/security/shinyhunters-resurfaces-after-fbi-arrests-uses-old-pgp-keys-as-proof/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-9078000bd51b)
- [European Commission confirms data theft in EU Academy breach](https://www.bleepingcomputer.com/news/security/european-commission-confirms-data-theft-in-eu-academy-breach/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-0ddde081cc79)
- [Hackers compromise Check Point Servers in 22 organizations](https://www.bleepingcomputer.com/news/security/hackers-compromise-check-point-servers-in-22-organizations/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-53f2a1acf596)
- [Police disrupt 57 illegal streaming services with 7.3 million visits](https://www.bleepingcomputer.com/news/security/police-disrupt-57-illegal-streaming-services-with-73-million-visits/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-d8bd69410276)
- [From Vulnerability Noise to Resilience: Rethinking Security in the AI Era](https://www.bleepingcomputer.com/news/security/from-vulnerability-noise-to-resilience-rethinking-security-in-the-ai-era/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-24/#reporting-1f0ade1a2280)
