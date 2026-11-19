# GRC Intelligence Report - 2026-11-19
**Generated:** 2026-11-19T00:35:10.402883Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/1f6adc21187d51b8b0e8c72966d793a25b0c0cef/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-19](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Active exploitation of critical vulnerabilities in widely deployed infrastructure components including NGINX, Apache Roller, Perforce Puppet, and F5 BIG-IP demands immediate asset identification and remediation verification across internet-facing and internal systems. The addition of Perforce Puppet to the CISA Known Exploited Vulnerabilities catalog elevates urgency for configuration management platforms that underpin automated environments. [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html); [Critical Apache Roller RCE Flaw Under Active Exploitation, No Authentication Required](https://thehackernews.com/2026/11/critical-apache-roller-rce-flaw-under.html); [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html); [F5 Warns 6 Critical BIG-IP Flaws Can Crash Traffic in Specific Setups, May Allow RCE](https://thehackernews.com/2026/11/f5-warns-6-critical-big-ip-flaws-can.html)

Supply chain compromises affecting Microsoft's official Agent Framework Python package on PyPI and a reported cyberattack on IT provider Wellington IT extend risk to dependent organizations, requiring supplier assurance reviews and software composition analysis validation. These events demonstrate how single points of failure in shared services and trusted repositories can cascade across multiple entities. [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/); [Microsoft’s Agent Framework PyPI package compromised to steal credentials](https://www.bleepingcomputer.com/news/security/microsofts-agent-framework-pypi-package-compromised-to-steal-credentials/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### NGINX's HTTP/2 support enables unauthenticated code execution

**Review priority:** Medium · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** This decade-old vulnerability in a ubiquitous web server component weakens assurance that asset inventories capture long-standing exposures. The accountable owner should confirm that all NGINX instances with HTTP/2 enabled have been identified and patched to fixed versions.

**Source evidence:** “A flaw in NGINX's HTTP/2 support can allow an attacker to run code on servers with HTTP/2 enabled, without needing to log in. The decade-old flaw, CVE-2026-123007, dubbed "nginx2root," has been present in NGINX's open-source code since version 1.9.5, released on September 22, 2015. Fixed versions 1.31.9 and 1.30.7 came out today.” [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Apache Roller XML-RPC endpoint permits unauthenticated remote code execution

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a critical deserialization flaw in a widely used blogging platform undermines vulnerability management coverage for internet-facing applications. The accountable owner should confirm that any Apache Roller deployments have been assessed for exploitation and remediated.

**Source evidence:** “A critical security flaw in Apache Roller, an open-source, Java-based blogging platform, has come under active exploitation in the wild, according to the Apache Software Foundation &#40;ASF&#41; The vulnerability, tracked as CVE-2026-129448 &#40;CVSS score: 9.8&#41;, is a case of unauthenticated deserialization in the XML-RPC endpoint that could lead to remote code execution.” [Critical Apache Roller RCE Flaw Under Active Exploitation, No Authentication Required](https://thehackernews.com/2026/11/critical-apache-roller-rce-flaw-under.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Perforce Puppet enterprise infrastructure-as-code platform added to CISA exploited vulnerabilities catalog

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** CISA KEV inclusion signals active exploitation of a core infrastructure automation tool, extending risk to all dependent environments. The accountable owner should confirm that Perforce Puppet instances are inventoried, patched, and that supplier communications address exploitation evidence.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Tuesday added a critical security flaw impacting Perforce Puppet, an enterprise infrastructure-as-code &#40;IaC&#41; and configuration management platform, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing reports of active exploitation. The vulnerability, tracked as CVE-2026-115731 &#40;CVSS score: 9.4&#41;, is a case of…” [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### F5 BIG-IP Traffic Management Microkernel vulnerable to unauthenticated crash

**Review priority:** Medium · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Multiple critical flaws in a core traffic management component require configuration-specific exposure assessment beyond version checks. The accountable owner should confirm that BIG-IP deployments have been evaluated for the specific iRule and APM policy conditions that trigger the vulnerabilities.

**Source evidence:** “Six critical vulnerabilities in F5 BIG-IP allow an attacker to crash the Traffic Management Microkernel &#40;TMM&#41; without logging in, disrupting traffic until the TMM restarts. Each flaw needs a specific setup on a virtual server: an iRule that uses a particular command, or an APM policy that includes two particular kinds of agent. F5, which makes BIG-IP, disclosed the flaws today and says they…” [F5 Warns 6 Critical BIG-IP Flaws Can Crash Traffic in Specific Setups, May Allow RCE](https://thehackernews.com/2026/11/f5-warns-6-critical-big-ip-flaws-can.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Wellington IT exposes credit union member data in reported cyberattack

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A single IT provider breach compromising multiple credit unions demonstrates concentration risk in shared service dependencies. The accountable owner should confirm that supplier assurance programs cover data protection obligations and incident notification for critical third parties.

**Source evidence:** “A reported cyberattack on Wellington IT has exposed sensitive information belonging to members of 50 credit unions, the majority of which are located in Ireland…” [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Microsoft's official Agent Framework Python package compromised to steal cloud credentials

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Supply chain compromise of an official Microsoft package on a public repository undermines trust in dependency management controls. The accountable owner should confirm that software composition analysis detects malicious package versions and that developer credential rotation procedures are tested.

**Source evidence:** “Hackers compromised Microsoft's official Agent Framework Python package on PyPI, publishing two malicious versions designed to steal cloud credentials and other sensitive information from developers' systems…” [Microsoft’s Agent Framework PyPI package compromised to steal credentials](https://www.bleepingcomputer.com/news/security/microsofts-agent-framework-pypi-package-compromised-to-steal-credentials/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

## Source Highlights

- [10-Year-Old NGINX HTTP/2 Flaw Lets Unauthenticated Attackers Execute Code on Servers](https://thehackernews.com/2026/11/10-year-old-nginx-http2-flaw-lets.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-04e49dcbdb74)
- [Critical Apache Roller RCE Flaw Under Active Exploitation, No Authentication Required](https://thehackernews.com/2026/11/critical-apache-roller-rce-flaw-under.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-6ec0dce548ff)
- [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-5966ac56e61b)
- [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-eeab189c3475)
- [Ukraine, FBI arrest ransomware gang members tied to $40M in ransoms](https://www.bleepingcomputer.com/news/security/ukraine-fbi-arrest-ransomware-gang-members-tied-to-40m-in-ransoms/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-98624c3d23ee)
- [Russia's Cold Relic APT Turns One Cloud Breach Into Another](https://www.darkreading.com/cyberattacks-data-breaches/cold-relic-turns-one-cloud-breach-into-another) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-597438bcf54f)
- [Coinbase blocks $4.7 million in transfers to Elon Musk deepfake scam](https://www.bleepingcomputer.com/news/security/coinbase-blocks-47-million-in-transfers-to-elon-musk-deepfake-scam/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-3208f46dd169)
- [Strike Graph Launches Integration AI to Automate Continuous Compliance Evidence Using Any Existing Tool](https://www.darkreading.com/cyber-risk/strike-graph-launches-integration-ai-to-automate-continuous-compliance-evidence-using-any-existing-tool) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-2a612a97044a)
- [AttackIQ Research Reveals How Iranian Cyber Groups Hand Off Network Access to Enable Destructive Attacks](https://www.darkreading.com/threat-intelligence/attackiq-research-reveals-iranian-cyber-groups) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-598072de3005)
- [Data breach impacts 40 Irish credit unions in reported IT provider hack](https://www.bleepingcomputer.com/news/security/data-breach-impacts-40-irish-credit-unions-in-reported-it-provider-hack/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-c3f1d9d987e8)
- [F5 Warns 6 Critical BIG-IP Flaws Can Crash Traffic in Specific Setups, May Allow RCE](https://thehackernews.com/2026/11/f5-warns-6-critical-big-ip-flaws-can.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-4ab4f5e03685)
- [Microsoft’s Agent Framework PyPI package compromised to steal credentials](https://www.bleepingcomputer.com/news/security/microsofts-agent-framework-pypi-package-compromised-to-steal-credentials/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-19/#reporting-97ef079b76ea)
