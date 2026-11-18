# GRC Intelligence Report - 2026-11-18
**Generated:** 2026-11-18T21:15:44.569711Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/a192581edc4bf0fb5840d4ebc439ce826be24971/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-18](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Critical vulnerabilities in foundational infrastructure components are under active exploitation, requiring immediate vulnerability management review. CISA has added a Perforce Puppet flaw to its Known Exploited Vulnerabilities catalog, a decade-old NGINX HTTP/2 flaw enables unauthenticated code execution, and a Java runtime vulnerability affects Jira, Jenkins, and Keycloak. These exposures weaken assurance across web servers, automation platforms, and enterprise applications. Vulnerability owners must confirm affected assets are identified and remediation or compensating controls are validated. [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html); [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html); [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)

Supply chain compromises and evolving social engineering tactics extend third-party risk and access management challenges. Microsoft's official Agent Framework PyPI package was compromised to steal cloud credentials, a Wellington IT breach exposed data from 50 credit unions, and attackers are using deepfakes with helpdesk impersonation to bypass identity verification. These events weaken supplier assurance and identity control effectiveness. Supplier risk and identity owners should review dependency verification, supplier access scope, and verification control resilience. [Microsoft’s Agent Framework PyPI package compromised to steal credentials](https://www.bleepingcomputer.com/news/security/microsofts-agent-framework-pypi-package-compromised-to-steal-credentials/); [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/); [From Deepfakes to Helpdesk Impersonation: Why Stronger Verification Matters](https://www.bleepingcomputer.com/news/security/from-deepfakes-to-helpdesk-impersonation-why-stronger-verification-matters/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Perforce Puppet flaw added to CISA KEV catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a widely used infrastructure automation platform weakens vulnerability management assurance. The vulnerability owner should confirm affected instances are identified and remediation or compensating controls are in place.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Tuesday added a critical security flaw impacting Perforce Puppet, an enterprise infrastructure-as-code &#40;IaC&#41; and configuration management platform, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing reports of active exploitation. The vulnerability, tracked as CVE-2026-115731 &#40;CVSS score: 9.4&#41;, is a case of…” [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### NGINX HTTP/2 support flaw enables unauthenticated code execution

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** A decade-old vulnerability in a ubiquitous web server component weakens vulnerability management assurance across exposed services. The asset owner should verify all NGINX instances are upgraded to fixed versions or have compensating controls.

**Source evidence:** “A flaw in NGINX's HTTP/2 support can allow an attacker to run code on servers with HTTP/2 enabled, without needing to log in. The decade-old flaw, CVE-2026-123007, dubbed "nginx2root," has been present in NGINX's open-source code since version 1.9.5, released on September 22, 2015. Fixed versions 1.31.9 and 1.30.7 came out today.” [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Java4Shell flaw enables pre-authentication remote code execution

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** A memory corruption vulnerability in the OpenJDK runtime weakens vulnerability management assurance for critical enterprise applications. The application owner should confirm affected Java versions are identified and patched or mitigated.

**Source evidence:** “A Java flaw called Java4Shell can let attackers without an account run their own code on Jira, Jenkins, Keycloak, and three other widely used applications, says Calif, the security research firm that disclosed it this week. The flaw is present in Java 17.0.6 and later, and the vulnerable code runs only on x86-64 Intel and AMD chips that support the AVX-512 VBMI feature.” [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Microsoft Agent Framework PyPI package compromised to steal credentials

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A supply chain compromise of an official Microsoft package weakens third-party risk assurance for development pipelines. The dependency owner should verify whether malicious versions were consumed and rotate any exposed credentials.

**Source evidence:** “Hackers compromised Microsoft's official Agent Framework Python package on PyPI, publishing two malicious versions designed to steal cloud credentials and other sensitive information from developers' systems…” [Microsoft’s Agent Framework PyPI package compromised to steal credentials](https://www.bleepingcomputer.com/news/security/microsofts-agent-framework-pypi-package-compromised-to-steal-credentials/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Wellington IT cyberattack exposes credit union member data

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A supplier compromise exposing sensitive financial data weakens third-party risk assurance and data protection controls. The supplier risk owner should review Wellington IT access scope and assurance evidence for affected credit unions.

**Source evidence:** “A reported cyberattack on Wellington IT has exposed sensitive information belonging to members of 50 credit unions, the majority of which are located in Ireland…” [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Deepfake and helpdesk impersonation attacks bypass identity verification

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** Evolving social engineering tactics using AI-generated deepfakes weaken access management assurance for identity verification. The identity owner should confirm verification controls resist impersonation and deepfake-based deception.

**Source evidence:** “Attackers are using deepfakes, helpdesk impersonation, and fake IT support requests to deceive employees and gain unauthorized access to corporate systems. Specops Software examines real-world attacks and explains how stronger identity verification can help organizations prevent social engineering threats…” [From Deepfakes to Helpdesk Impersonation: Why Stronger Verification Matters](https://www.bleepingcomputer.com/news/security/from-deepfakes-to-helpdesk-impersonation-why-stronger-verification-matters/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

## Source Highlights

- [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-04e49dcbdb74)
- [Critical Apache Roller RCE Flaw Under Active Exploitation, No Authentication Required](https://thehackernews.com/2026/11/critical-apache-roller-rce-flaw-under.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-6ec0dce548ff)
- [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-5966ac56e61b)
- [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-eeab189c3475)
- [Coinbase blocks $4.7 million in transfers to Elon Musk deepfake scam](https://www.bleepingcomputer.com/news/security/coinbase-blocks-47-million-in-transfers-to-elon-musk-deepfake-scam/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-3208f46dd169)
- [Strike Graph Launches Integration AI to Automate Continuous Compliance Evidence Using Any Existing Tool](https://www.darkreading.com/cyber-risk/strike-graph-launches-integration-ai-to-automate-continuous-compliance-evidence-using-any-existing-tool) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-2a612a97044a)
- [AttackIQ Research Reveals How Iranian Cyber Groups Hand Off Network Access to Enable Destructive Attacks](https://www.darkreading.com/threat-intelligence/attackiq-research-reveals-iranian-cyber-groups) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-598072de3005)
- [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-c3f1d9d987e8)
- [F5 Warns 6 Critical BIG-IP Flaws Can Crash Traffic in Specific Setups, May Allow RCE](https://thehackernews.com/2026/11/f5-warns-6-critical-big-ip-flaws-can.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-4ab4f5e03685)
- [Microsoft’s Agent Framework PyPI package compromised to steal credentials](https://www.bleepingcomputer.com/news/security/microsofts-agent-framework-pypi-package-compromised-to-steal-credentials/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-97ef079b76ea)
- [Java4Shell Flaw Threatens Global Enterprises, Java Application Ecosystem](https://www.darkreading.com/vulnerabilities-threats/java4shell-flaw-threatens-global-java-application-ecosystem) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-b614b4646977)
- [From Deepfakes to Helpdesk Impersonation: Why Stronger Verification Matters](https://www.bleepingcomputer.com/news/security/from-deepfakes-to-helpdesk-impersonation-why-stronger-verification-matters/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-993f9d718221)
