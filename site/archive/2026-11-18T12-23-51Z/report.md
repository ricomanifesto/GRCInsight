# GRC Intelligence Report - 2026-11-18
**Generated:** 2026-11-18T12:23:51.418823Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/38af4f324e5957d72ebb9ed34e4dd874aff98b31/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-18](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Supply chain attacks against the Microsoft agent-framework PyPI package and the Optimizely experience platform have demonstrated how trusted third-party dependencies can be weaponized to steal cloud credentials and distribute malware to high-traffic websites. These incidents elevate third-party risk management as a priority for control owners who must now verify supplier assurance evidence and enforce strict content security policies across web assets. [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html); [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)

Concurrently, CISA has added the Perforce Puppet RCE to its Known Exploited Vulnerabilities catalog and urged immediate patching of the Java4Shell flaw in Oracle Java, while Apache Roller exploits are actively compromising servers. These developments require vulnerability management owners to accelerate asset identification, emergency patching, and monitoring coverage for the affected platforms. [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html); [CISA Urges Immediate Patching of Java4Shell Flaw That Could Allow Remote Code Execution](https://thehackernews.com/2026/11/cisa-urges-immediate-patching-of.html); [Apache warns of Roller RCE vulnerability exploited in attacks](https://www.bleepingcomputer.com/news/security/apache-warns-of-roller-rce-vulnerability-exploited-in-attacks/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Microsoft agent-framework PyPI package compromised to steal cloud credentials

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** The supply chain compromise of a Microsoft Python package demonstrates how third-party dependencies can bypass perimeter controls and exfiltrate cloud credentials. Supplier risk owners should verify whether the agent-framework package is used in build pipelines and confirm remediation evidence from Microsoft.

**Source evidence:** “Threat actors have compromised Microsoft's agent-framework package to push a credential stealer, according to reports from Aikido, Chainguard, Endor Labs, OX Security, SafeDep, Socket, StepSecurity, and Google-owned Wiz. The malicious versions, 1.26.1 and 1.26.2, were published 33 minutes apart on November 17, 2026, and are designed to run a credential stealer on every Python start.” [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Optimizely platform exploited to distribute malware to 178 top websites

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** The Optimizely supply chain attack shows that third-party experience platforms can become malware distribution vectors affecting high-profile websites. Third-party risk owners should assess dependencies on Optimizely and similar services and validate content security policies.

**Source evidence:** “At least 178 top web destinations unwittingly served a variety of malware exploits against visitors over the past 24 hours thanks to a security vulnerability involving Optimizely, a company that helps websites customize user experiences and test out new features. Experts say the incident, which saw data-stealing malicious software silently injected into sites like the BBC, CNN, Equifax, Ledger and Zoom, was exacerbated by the reality that few popular websites enforce strict rules on the sources of third-party content.” [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Perforce Puppet enterprise infrastructure-as-code platform added to CISA KEV catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Adding the Puppet RCE to the CISA KEV catalog elevates the urgency for vulnerability management programs to identify and remediate affected instances. Vulnerability and asset owners should confirm the inventory of deployed Puppet servers and the status of emergency patching or compensating controls.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Tuesday added a critical security flaw impacting Perforce Puppet, an enterprise infrastructure-as-code &#40;IaC&#41; and configuration management platform, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing reports of active exploitation.” [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Oracle Java critical flaw requires immediate patching per CISA

**Review priority:** High · Monitoring and detection · Owner: Detection and monitoring owner

**Why it matters:** CISA's urgent patching directive for the Java4Shell vulnerability heightens the need for continuous vulnerability monitoring and rapid remediation workflows. Monitoring and detection owners should ensure telemetry covers Java version inventory and exploitation attempts.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; has urged organizations to immediately patch a newly disclosed critical security flaw impacting Oracle Java. The flaw, tracked as CVE-2026-114938 &#40;CVSS score: 8.1&#41;, refers to a case of out-of-bounds write that can lead to denial-of-service &#40;DoS&#41; or remote code execution under certain conditions.” [CISA Urges Immediate Patching of Java4Shell Flaw That Could Allow Remote Code Execution](https://thehackernews.com/2026/11/cisa-urges-immediate-patching-of.html)

**Evidence to request:** Log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

**Reference controls:** ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)

### Apache Roller critical flaw exploited for remote code execution

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of the Apache Roller RCE requires immediate vulnerability management attention for any deployed Roller instances. Vulnerability and asset owners should identify affected Roller servers and apply security updates or isolate them.

**Source evidence:** “Apache has released security updates to address a critical Roller flaw that threat actors are exploiting to gain code execution on vulnerable servers” [Apache warns of Roller RCE vulnerability exploited in attacks](https://www.bleepingcomputer.com/news/security/apache-warns-of-roller-rce-vulnerability-exploited-in-attacks/)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Google Workspace data leveraged to breach second organization

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** The Cold Relic campaign demonstrates how a single cloud identity compromise can cascade into multiple organizations through trusted relationships. Access management owners should review Google Workspace access controls and monitor for anomalous cross-tenant activity.

**Source evidence:** “The Russia-linked cyber espionage group known as Cold Relic &#40;formerly COLDRIVER and UNC4057&#41; has been observed weaponizing a single cloud compromise into a launchpad for a series of linked intrusions resulting in third-party compromise. Google's Mandiant and Threat Intelligence Group &#40;GTIG&#41; said it investigated a 2026 compromise at a U.S.-based organization in which the adversary leveraged” [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

## Source Highlights

- [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-eeab189c3475)
- [CISA Urges Immediate Patching of Java4Shell Flaw That Could Allow Remote Code Execution](https://thehackernews.com/2026/11/cisa-urges-immediate-patching-of.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-e73903040477)
- [Dizigom illegal streaming service with 21M monthly visits shuts down](https://www.bleepingcomputer.com/news/security/dizigom-illegal-streaming-service-with-21m-monthly-visits-shuts-down/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-75d2be14123c)
- [Apache warns of Roller RCE vulnerability exploited in attacks](https://www.bleepingcomputer.com/news/security/apache-warns-of-roller-rce-vulnerability-exploited-in-attacks/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-4d4692262fd0)
- [Microsoft announces Windows Server 2028 with hardened security](https://www.bleepingcomputer.com/news/microsoft/microsoft-announces-windows-server-2028-with-hardened-security/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-3cc7c5217114)
- [British Scattered Spider hacker sentenced to 6 years in prison](https://www.bleepingcomputer.com/news/security/british-scattered-spider-hacker-sentenced-to-6-years-in-prison/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-9f8e9c27a393)
- [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-533b590042a0)
- [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-4816a5c313d5)
- [Java4Shell Flaw \(CVE-2026-114938\) Enables Pre-Auth RCE in Jira, Jenkins, Keycloak and More](https://thehackernews.com/2026/11/java4shell-cve-2026-114938-enables-pre.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-5966ac56e61b)
- [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-e010dc913600)
- [Critical Java4Shell flaw allows RCE attacks on major Java applications](https://www.bleepingcomputer.com/news/security/critical-java4shell-flaw-allows-rce-attacks-on-major-java-applications/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-fca3dc2fb776)
- [Optimizely Malware Attacks Highlight Third-Party Vendor Risks](https://www.darkreading.com/cyber-risk/optimizely-malware-attacks-third-party-vendor-risks) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/#reporting-eca290345628)
