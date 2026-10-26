# GRC Intelligence Report - 2026-10-26
**Generated:** 2026-10-26T18:32:27.578851Z
**Date of Issue:** October 2026
**Analysis Period:** October 2026
**Source:** [SentryDigest](https://ricomanifesto.github.io/SentryDigest/feed.xml)
**Source Issue:** [SentryDigest 2026-10-26](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Make confirmed exposure the basis for remediation and access-control decisions. Start by checking which reported conditions apply to “Collabora Online Built-in CODE Server” [CISA Flags Two Actively Exploited Critical Flaws in Collabora Online and Arista VeloCloud](https://thehackernews.com/2026/10/cisa-flags-two-actively-exploited.html), “Microsoft 365 campaign” [Microsoft 365 Token-Replay Attacks Compromise 97 Accounts at 79 Organizations](https://thehackernews.com/2026/10/microsoft-365-token-replay-attacks.html), and “Android spyware kit called uCreator” [uCreator Android Spyware Can Steal Telegram 2FA Passwords and Clone WeChat Accounts](https://thehackernews.com/2026/10/ucreator-android-spyware-can-steal.html). Use that assessment to decide where control evidence is sufficient and where an owner needs to investigate.

First, establish affected-asset and configuration scope. Next, test the relevant account and permission boundaries. Then, establish the relevant data and access scope. These are proposed review priorities: confirm local applicability before assigning work. In each case, record the applicability decision and the evidence supporting the next step.

The supplied evidence does not establish your organization's exposure or control effectiveness. No primary-source regulatory change is established by this selection. Revise the agenda if the relevant product, activity or dependency is absent, or if stronger evidence changes the assessment.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

### Collabora Online Built-in CODE Server — Vulnerability management

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Friday added two vulnerabilities impacting Collabora Online Built-in CODE Server and Arista VeloCloud Orchestrator &#40;VCO&#41; to its Known Exploited Vulnerabilities &#40;KEV&#41;, citing reports of active exploitation in the wild. The critical-severity vulnerabilities are listed below - CVE-2026-110447 &#40;CVSS score: 9.2&#41; - An operating” [CISA Flags Two Actively Exploited Critical Flaws in Collabora Online and Arista VeloCloud](https://thehackernews.com/2026/10/cisa-flags-two-actively-exploited.html)

**Control decision (inference):** A remediation decision depends on matching deployed assets to the source's exposure conditions.

**Inferred review priority:** High. **Owner:** Vulnerability and asset owners. **Evidence to request:** affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

### Microsoft 365 campaign — Access management

**Source evidence:** “Cybersecurity researchers have disclosed a Microsoft 365 campaign that has been observed leveraging an adversary-in-the-middle &#40;AitM&#41; relay to capture sign-in sessions and then replay the stolen tokens to break into email accounts at 79 organizations. Huntress, which observed the activity between July 14 and September 22, 2026, said it detected 497 successful Microsoft 365 sign-in events across” [Microsoft 365 Token-Replay Attacks Compromise 97 Accounts at 79 Organizations](https://thehackernews.com/2026/10/microsoft-365-token-replay-attacks.html)

**Control decision (inference):** An access-control decision depends on whether the reported path crosses a permission boundary in your environment.

**Inferred review priority:** High. **Owner:** Identity and access owner. **Evidence to request:** access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

### Android spyware kit called uCreator — Data protection

**Source evidence:** “A rentable Android spyware kit called uCreator takes over Telegram and WeChat accounts by hiding its code inside working copies of the two apps, researcher Ovi found. It only reaches people who install one of these tampered copies, spread outside the official app stores, or who run WeChat inside the kit makers' own container app. The kit's Telegram part matches Baohuo, a backdoor that Doctor” [uCreator Android Spyware Can Steal Telegram 2FA Passwords and Clone WeChat Accounts](https://thehackernews.com/2026/10/ucreator-android-spyware-can-steal.html)

**Control decision (inference):** A data-protection decision depends on the data involved and the controls governing access to it.

**Inferred review priority:** Medium. **Owner:** Data and privacy owners. **Evidence to request:** data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

### PHP2Shell — Vulnerability management

**Source evidence:** “Two critical RCE vulnerabilities &#40;CVE-2026-109618 and CVE-2026-109619&#41;, collectively tracked as PHP2Shell, have been successfully exploited in the wild” [PHP2Shell security flaws now sucessfully exploited in the wild](https://www.bleepingcomputer.com/news/security/php2shell-security-flaws-now-sucessfully-exploited-in-the-wild/)

**Control decision (inference):** A remediation decision depends on matching deployed assets to the source's exposure conditions.

**Inferred review priority:** High. **Owner:** Vulnerability and asset owners. **Evidence to request:** affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

### runaway agents — Governance and accountability

**Source evidence:** “A new NIST, CISA, and NSA guide treats runaway agents as incidents to be rehearsed. The hard part of the response is answering whose authority the agent used, and that answer has to exist before the incident does” [When an AI Agent Is the Incident, the Identity Record Is the Evidence](https://www.bleepingcomputer.com/news/security/when-an-ai-agent-is-the-incident-the-identity-record-is-the-evidence/)

**Control decision (inference):** An assurance decision depends on whether the development changes an assumption used by your control owners.

**Inferred review priority:** Medium. **Owner:** Risk and control owners. **Evidence to request:** the affected assumption, accountable owner and a recorded decision to act or accept risk.

**Decision trigger:** If an assumption no longer holds, record an accountable decision to change the control or accept the resulting uncertainty.

### network detection and response &#40;NDR&#41; platform — Monitoring and detection

**Source evidence:** “Every SOC struggles with a pile of alerts. Very few of those alerts explain how an attack started or how it progressed. Network data, like that from a network detection and response &#40;NDR&#41; platform, connects individual alerts into one timeline, and it feeds the defensive systems that can tie all events together into one coordinated view. SOC teams often first see the shape of an intrusion” [Between alerts: What Attackers Do in the Spaces Ordinary Detection Misses](https://thehackernews.com/2026/10/between-alerts-what-attackers-do-in.html)

**Control decision (inference):** A monitoring decision depends on distinguishing the reported behavior from authorized activity in your telemetry.

**Inferred review priority:** Medium. **Owner:** Detection and monitoring owner. **Evidence to request:** log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

## Source Highlights

- [PHP2Shell security flaws now sucessfully exploited in the wild](https://www.bleepingcomputer.com/news/security/php2shell-security-flaws-now-sucessfully-exploited-in-the-wild/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-7c54e769948b)
- [Brotli Decoder Flaw Behind Node.js RCE Also Affects Bun, Python and Other Widely Used Software](https://thehackernews.com/2026/10/brotli-decoder-flaw-behind-nodejs-rce.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-a64123d82829)
- [CISA Flags Two Actively Exploited Critical Flaws in Collabora Online and Arista VeloCloud](https://thehackernews.com/2026/10/cisa-flags-two-actively-exploited.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-ad7396463092)
- [⚡ Weekly Recap: This2Shell, That2Shell, Everything's an RCE? Rogue AI, Supply Chain Chaos and More](https://thehackernews.com/2026/10/weekly-recap-this2shell-that2shell.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-e0df996ac6f2)
- [When an AI Agent Is the Incident, the Identity Record Is the Evidence](https://www.bleepingcomputer.com/news/security/when-an-ai-agent-is-the-incident-the-identity-record-is-the-evidence/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-f0b80253de2a)
- [10 Software Security Practices Built for the Next 250 Years](https://www.darkreading.com/cyberattacks-data-breaches/10-software-security-practices-built-250-years) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-9d30cfebb912)
- [Chinese man extradited for role in $36 million cryptocurrency scam](https://www.bleepingcomputer.com/news/security/chinese-man-extradited-for-role-in-36-million-cryptocurrency-scam/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-5a51b4b30386)
- [Two Critical Wasmtime Flaws Could Let Malicious WebAssembly Modules Escape Sandboxes](https://thehackernews.com/2026/10/two-critical-wasmtime-flaws-could-let.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-f67f5ee9f8e3)
- [Between alerts: What Attackers Do in the Spaces Ordinary Detection Misses](https://thehackernews.com/2026/10/between-alerts-what-attackers-do-in.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-ce0386ac2297)
- [Kali Linux 2026.3 released with 6 new tools, desktop updates](https://www.bleepingcomputer.com/news/linux/kali-linux-20263-released-with-6-new-tools-desktop-updates/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-982f2ce76891)
- [uCreator Android Spyware Can Steal Telegram 2FA Passwords and Clone WeChat Accounts](https://thehackernews.com/2026/10/ucreator-android-spyware-can-steal.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-20494af63ce3)
- [Microsoft 365 Token-Replay Attacks Compromise 97 Accounts at 79 Organizations](https://thehackernews.com/2026/10/microsoft-365-token-replay-attacks.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-10-26/#reporting-399172439712)
