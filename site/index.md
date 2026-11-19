# GRC Intelligence Report - 2026-11-19
**Generated:** 2026-11-19T06:30:02.743185Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/80230dbb4041dbdfbe1281446345e218ffa49ed0/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-19](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Critical vulnerabilities in widely deployed infrastructure components including NGINX, Perforce Puppet, Apache Roller, Java runtime, and F5 BIG-IP are under active exploitation or have fixes released, requiring immediate asset identification and remediation verification by vulnerability management owners. [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html); [Critical Apache Roller RCE Flaw Under Active Exploitation, No Authentication Required](https://thehackernews.com/2026/11/critical-apache-roller-rce-flaw-under.html); [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html); [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html); [F5 Warns 6 Critical BIG-IP Flaws Can Crash Traffic in Specific Setups, May Allow RCE](https://thehackernews.com/2026/11/f5-warns-6-critical-big-ip-flaws-can.html)

A supply chain breach at Wellington IT exposed sensitive data of 50 credit unions while law enforcement arrested ransomware operators linked to $40.5 million in payments, underscoring the need for third-party risk assurance and incident response readiness. [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### NGINX HTTP/2 support enables unauthenticated remote code execution via decade-old flaw

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** A long-standing unauthenticated remote code execution flaw in a ubiquitous web server weakens vulnerability management by exposing potentially unpatched instances. The accountable owner should identify all NGINX deployments with HTTP/2 enabled and confirm application of fixed versions.

**Source evidence:** “A flaw in NGINX's HTTP/2 support can allow an attacker to run code on servers with HTTP/2 enabled, without needing to log in. The decade-old flaw, CVE-2026-123007, dubbed "nginx2root," has been present in NGINX's open-source code since version 1.9.5, released on September 22, 2015. Fixed versions 1.31.9 and 1.30.7 came out today.” [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Apache Roller suffers active exploitation via unauthenticated deserialization flaw

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a critical deserialization flaw in a blogging platform weakens vulnerability management by indicating that unpatched instances are being compromised. The accountable owner should verify whether Apache Roller is deployed and ensure the XML-RPC endpoint is secured or patched.

**Source evidence:** “A critical security flaw in Apache Roller, an open-source, Java-based blogging platform, has come under active exploitation in the wild, according to the Apache Software Foundation &#40;ASF&#41; The vulnerability, tracked as CVE-2026-129448 &#40;CVSS score: 9.8&#41;, is a case of unauthenticated deserialization in the XML-RPC endpoint that could lead to remote code execution.” [Critical Apache Roller RCE Flaw Under Active Exploitation, No Authentication Required](https://thehackernews.com/2026/11/critical-apache-roller-rce-flaw-under.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Java4Shell flaw enables pre-authentication remote code execution across multiple enterprise applications

**Review priority:** Medium · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** A hardware-dependent Java flaw affecting widely used enterprise applications weakens vulnerability management by creating a conditional exposure that may be overlooked. The accountable owner should inventory affected Java versions on relevant hardware and assess applicability of mitigations.

**Source evidence:** “A Java flaw called Java4Shell can let attackers without an account run their own code on Jira, Jenkins, Keycloak, and three other widely used applications, says Calif, the security research firm that disclosed it this week. The flaw is present in Java 17.0.6 and later, and the vulnerable code runs only on x86-64 Intel and AMD chips that support the AVX-512 VBMI feature.” [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Perforce Puppet joins CISA Known Exploited Vulnerabilities catalog signaling active exploitation

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a critical infrastructure-as-code platform weakens vulnerability management assurance by confirming that unpatched instances are being targeted. The accountable owner should confirm affected asset inventory and verify remediation or compensating controls are in place.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Tuesday added a critical security flaw impacting Perforce Puppet, an enterprise infrastructure-as-code &#40;IaC&#41; and configuration management platform, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing reports of active exploitation.” [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### F5 BIG-IP critical vulnerabilities allow unauthenticated Traffic Management Microkernel crashes

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Multiple critical flaws in a core application delivery platform weaken vulnerability management by enabling unauthenticated disruption of traffic management. The accountable owner should identify affected BIG-IP configurations and validate remediation or compensating controls.

**Source evidence:** “Six critical vulnerabilities in F5 BIG-IP allow an attacker to crash the Traffic Management Microkernel &#40;TMM&#41; without logging in, disrupting traffic until the TMM restarts. Each flaw needs a specific setup on a virtual server: an iRule that uses a particular command, or an APM policy that includes two particular kinds of agent.” [F5 Warns 6 Critical BIG-IP Flaws Can Crash Traffic in Specific Setups, May Allow RCE](https://thehackernews.com/2026/11/f5-warns-6-critical-big-ip-flaws-can.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Wellington IT cyberattack exposes sensitive data of 50 credit unions

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A supply chain breach at an IT provider compromising sensitive financial data weakens third-party risk assurance by demonstrating cascading impact across multiple regulated entities. The accountable owner should review supplier dependencies, assurance evidence, and escalation contacts for similar providers.

**Source evidence:** “A reported cyberattack on Wellington IT has exposed sensitive information belonging to members of 50 credit unions, the majority of which are located in Ireland…” [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

## Source Highlights

- [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-04e49dcbdb74)
- [Critical Apache Roller RCE Flaw Under Active Exploitation, No Authentication Required](https://thehackernews.com/2026/11/critical-apache-roller-rce-flaw-under.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-6ec0dce548ff)
- [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-5966ac56e61b)
- [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-eeab189c3475)
- [PHP Warns of Critical Security Flaws Affecting All Supported Versions, Fixes Coming November 19](https://thehackernews.com/2026/11/php-warns-of-critical-security-flaws.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-75b5f9594128)
- [Ukraine, FBI arrest ransomware gang members tied to $40M in ransoms](https://www.bleepingcomputer.com/news/security/ukraine-fbi-arrest-ransomware-gang-members-tied-to-40m-in-ransoms/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-98624c3d23ee)
- [Russia's Cold Relic APT Turns One Cloud Breach Into Another](https://www.darkreading.com/cyberattacks-data-breaches/cold-relic-turns-one-cloud-breach-into-another) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-597438bcf54f)
- [Coinbase blocks $4.7 million in transfers to Elon Musk deepfake scam](https://www.bleepingcomputer.com/news/security/coinbase-blocks-47-million-in-transfers-to-elon-musk-deepfake-scam/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-3208f46dd169)
- [Strike Graph Launches Integration AI to Automate Continuous Compliance Evidence Using Any Existing Tool](https://www.darkreading.com/cyber-risk/strike-graph-launches-integration-ai-to-automate-continuous-compliance-evidence-using-any-existing-tool) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-2a612a97044a)
- [AttackIQ Research Reveals How Iranian Cyber Groups Hand Off Network Access to Enable Destructive Attacks](https://www.darkreading.com/threat-intelligence/attackiq-research-reveals-iranian-cyber-groups) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-598072de3005)
- [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-c3f1d9d987e8)
- [F5 Warns 6 Critical BIG-IP Flaws Can Crash Traffic in Specific Setups, May Allow RCE](https://thehackernews.com/2026/11/f5-warns-6-critical-big-ip-flaws-can.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-4ab4f5e03685)
