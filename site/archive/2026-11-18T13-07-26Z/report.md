# GRC Intelligence Report - 2026-11-18
**Generated:** 2026-11-18T13:07:26.596673Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://sentrydigest.ricomanifesto.com/feed.xml)
**Source Issue:** [SentryDigest 2026-11-18](https://sentrydigest.ricomanifesto.com/archive/2026-11-18/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Active exploitation of critical infrastructure-as-code and Java runtime vulnerabilities, combined with software supply chain compromises affecting Microsoft and Optimizely platforms, weakens vulnerability management and third-party risk controls across enterprise environments. CISA has added a Perforce Puppet flaw to its Known Exploited Vulnerabilities catalog and urged immediate patching of a Java4Shell defect, while threat actors weaponized a Microsoft PyPI package and an experience optimization platform to steal credentials and distribute malware at scale. Vulnerability and asset owners should verify remediation status for Puppet and Java deployments, and supplier risk owners should assess exposure to the compromised agent-framework and Optimizely integrations. [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html); [CISA Urges Immediate Patching of Java4Shell Flaw That Could Allow Remote Code Execution](https://thehackernews.com/2026/11/cisa-urges-immediate-patching-of.html); [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html); [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)

A Russia-linked espionage group leveraged stolen Google Workspace credentials to breach a second U.S. organization, demonstrating how cloud identity compromise enables lateral movement across trusted relationships, while the sentencing of a Scattered Spider leader confirms accountability for identity-focused intrusions. Identity and access owners should confirm that federated credential scopes prevent cross-organization abuse and that session revocation controls are tested, and risk owners should validate that Scattered Spider tactics are covered in threat models and response playbooks. [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html); [British Scattered Spider hacker sentenced to 6 years in prison](https://www.bleepingcomputer.com/news/security/british-scattered-spider-hacker-sentenced-to-6-years-in-prison/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Perforce Puppet added to CISA Known Exploited Vulnerabilities catalog

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a critical infrastructure-as-code platform weakens vulnerability management assurance by confirming the flaw is being weaponized. Vulnerability and asset owners should confirm whether deployed Puppet instances meet the exposure conditions and verify remediation status.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Tuesday added a critical security flaw impacting Perforce Puppet, an enterprise infrastructure-as-code &#40;IaC&#41; and configuration management platform, to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, citing reports of active exploitation.” [Hackers Exploiting Critical Puppet RCE Flaw Affecting Enterprise Management Servers](https://thehackernews.com/2026/11/hackers-exploiting-critical-puppet-rce.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Oracle Java flaw prompts CISA urgent patching advisory

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** CISA's urgent patching directive for a widely deployed runtime indicates active exploitation risk, weakening vulnerability management timelines. Vulnerability and asset owners should identify affected Java deployments, verify patch deployment, and document any compensating controls.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; has urged organizations to immediately patch a newly disclosed critical security flaw impacting Oracle Java. The flaw, tracked as CVE-2026-114938 &#40;CVSS score: 8.1&#41;, refers to a case of out-of-bounds write that can lead to denial-of-service &#40;DoS&#41; or remote code execution under certain conditions.” [CISA Urges Immediate Patching of Java4Shell Flaw That Could Allow Remote Code Execution](https://thehackernews.com/2026/11/cisa-urges-immediate-patching-of.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Microsoft's agent-framework package compromised to deliver credential stealer

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A compromised Microsoft PyPI package exposes software supply chain dependencies to credential theft, weakening third-party risk controls. Supplier risk owners should review whether the agent-framework package is used in build pipelines and confirm remediation assurance from Microsoft.

**Source evidence:** “Threat actors have compromised Microsoft's agent-framework package to push a credential stealer, according to reports from Aikido, Chainguard, Endor Labs, OX Security, SafeDep, Socket, StepSecurity, and Google-owned Wiz. The malicious versions, 1.26.1 and 1.26.2, were published 33 minutes apart on November 17, 2026, and are designed to run a credential stealer on every Python start.” [Attackers Compromise Microsoft's Agent Framework PyPI Package to Steal Cloud Credentials](https://thehackernews.com/2026/11/attackers-compromise-microsofts-agent.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Optimizely vulnerability enables malware delivery to 178 websites

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** A third-party experience platform compromise exposes downstream clients to mass malware distribution, weakening third-party risk controls for client-side dependencies. Supplier risk owners should review Optimizely integration scope, confirm content security policies restrict third-party sources, and verify vendor remediation.

**Source evidence:** “At least 178 top web destinations unwittingly served a variety of malware exploits against visitors over the past 24 hours thanks to a security vulnerability involving Optimizely, a company that helps websites customize user experiences and test out new features. Experts say the incident, which saw data-stealing malicious software silently injected into sites like the BBC, CNN, Equifax, Ledger and Zoom, was exacerbated by the reality that few popular websites enforce strict rules on the sources of third-party content.” [Attackers Used Optimizely to A/B Test Malware on Top Websites](https://krebsonsecurity.com/2026/11/attackers-used-optimizely-to-a-b-test-malware-on-top-websites/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Stolen Google Workspace data weaponized for linked intrusions

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** Credential theft from a cloud workspace enables lateral movement across trusted relationships, weakening access management controls for federated identities. Identity and access owners should confirm whether Google Workspace credentials are scoped to prevent cross-organization abuse and review session revocation evidence.

**Source evidence:** “The Russia-linked cyber espionage group known as Cold Relic &#40;formerly COLDRIVER and UNC4057&#41; has been observed weaponizing a single cloud compromise into a launchpad for a series of linked intrusions resulting in third-party compromise. Google's Mandiant and Threat Intelligence Group &#40;GTIG&#41; said it investigated a 2026 compromise at a U.S.-based organization in which the adversary leveraged…” [Russian COLD RELIC Hackers Use Stolen Google Workspace Data to Breach Second U.S. Organization](https://thehackernews.com/2026/11/russian-cold-relic-hackers-use-stolen.html)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### Scattered Spider cybercrime collective sentenced for multi-company hacking campaign

**Review priority:** Medium · Governance and accountability · Owner: Risk and control owners

**Why it matters:** Criminal sentencing of a threat actor leader reinforces accountability for identity-focused attacks, supporting governance assurance that law enforcement pursues intrusions. Risk and control owners should confirm whether Scattered Spider tactics are addressed in threat models and incident response playbooks.

**Source evidence:** “A leader of the Scattered Spider cybercrime collective has been sentenced to six years in prison in the United States for stealing millions in cryptocurrency and conspiring to hack a dozen companies…” [British Scattered Spider hacker sentenced to 6 years in prison](https://www.bleepingcomputer.com/news/security/british-scattered-spider-hacker-sentenced-to-6-years-in-prison/)

**Evidence to request:** The affected assumption, accountable owner and a recorded decision to act or accept risk.

**Decision trigger:** If an assumption no longer holds, record an accountable decision to change the control or accept the resulting uncertainty.

**Reference controls:** ISO/IEC 27001:2022 A.5.1 (policies for information security), A.5.2 (roles and responsibilities); NIST CSF 2.0 GV.RR (roles, responsibilities and authorities), GV.OV (oversight)

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
