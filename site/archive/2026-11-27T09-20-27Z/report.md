# GRC Intelligence Report - 2026-11-27
**Generated:** 2026-11-27T09:20:27.358923Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/e486ae18c3ce4aab8dbb8f7b3defc6dffd440a13/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-27](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Multiple widely used enterprise platforms are under active exploitation despite available patches, including Drupal core, GeoServer, and Mitel MiCollab, which now appear on the CISA Known Exploited Vulnerabilities catalog. Control owners must accelerate vulnerability identification and verification of compensating controls across these assets. [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html); [Hackers Exploit 10 Vulnerabilities Across Mitel, Juniper, Vates, and Danfoss Products](https://thehackernews.com/2026/11/hackers-exploit-10-vulnerabilities.html); [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html)

Novel attack vectors are succeeding against critical infrastructure and corporate identities, with AI-assisted breaches confirmed in Switzerland, a phishing campaign harvesting Google and Okta credentials, and a malicious Chrome extension exfiltrating Gmail messages. These developments demand updated incident response procedures, stronger authentication monitoring, and data protection reviews for browser-based risks. [Switzerland Confirms AI-Assisted Cyberattacks Breached Critical Infrastructure Operators](https://thehackernews.com/2026/11/switzerland-confirms-ai-assisted.html); [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/); [Remus malware steals Gmail messages via fake Google Sheets extension](https://www.bleepingcomputer.com/news/security/remus-malware-steals-gmail-messages-via-fake-google-sheets-extension/)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Drupal core faces active exploitation

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a highly critical Drupal core flaw means vulnerability and asset owners must identify all deployed Drupal instances and confirm patching or compensating controls are in place. The accountable owner should verify that affected assets are inventoried and remediation status is tracked.

**Source evidence:** “Drupal has warned of a new "highly critical" security flaw impacting Drupal core that it said has been exploited in the wild. The vulnerability, tracked as CVE-2026-136716 &#40;CVSS score: N/A&#41;, has been described as a case of improper checking for unusual or exceptional conditions. It also relates to CVE-2026-132165 aka Fail2Install in that it addresses remaining vulnerable installation states…” [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Mitel MiCollab appears in CISA KEV catalog

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** CISA adding Mitel MiCollab vulnerabilities to the Known Exploited Vulnerabilities catalog indicates supplier risk owners must review dependencies on Mitel products and request assurance evidence from the vendor. The accountable owner should confirm supplier access scope and remediation assurance.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Wednesday added 10 security flaws to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, including five vulnerabilities impacting Mitel MiCollab that were disclosed last week. The Mitel MiCollab vulnerabilities are listed below - CVE-2026-133275 &#40;CVSS score: 5.3&#41; - An arbitrary file upload vulnerability in the Audio, Web and…” [Hackers Exploit 10 Vulnerabilities Across Mitel, Juniper, Vates, and Danfoss Products](https://thehackernews.com/2026/11/hackers-exploit-10-vulnerabilities.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### GeoServer suffers active exploitation of patched flaws

**Review priority:** High · Monitoring and detection · Owner: Detection and monitoring owner

**Why it matters:** Active exploitation of GeoServer vulnerabilities after patches were released means monitoring and detection owners must verify telemetry can identify exploitation attempts against GeoServer deployments. The accountable owner should review log coverage and detection rules for arbitrary file read and unauthenticated RCE chains.

**Source evidence:** “Threat actors are actively exploiting two newly patched security flaws in GeoServer, according to watchTowr. The vulnerabilities in question are CVE-2026-120705 and CVE-2026-129243, details of which are below - CVE-2026-120705 &#40;CVSS score: 8.6&#41; - An arbitrary file read vulnerability that could enable an attacker to access local text files readable by the GeoServer process or fetch…” [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html)

**Evidence to request:** Log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

**Reference controls:** ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)

### critical infrastructure operators experience AI-assisted breaches

**Review priority:** High · Incident response · Owner: Incident response lead

**Why it matters:** Confirmed AI-assisted breaches against critical infrastructure operators require incident response leads to assess containment procedures for AI-driven attack vectors and ensure evidence preservation. The accountable owner should review response ownership and retained logs for such incidents.

**Source evidence:** “Attackers using AI agents have broken into computer systems at Swiss organizations in four of five confirmed attacks, the first such cases in the country, the country's cybersecurity agency said yesterday. Three of the attacks targeted critical infrastructure operators, and two of those succeeded, with no major disruptions reported. The victims have not been named, and it is not known who is…” [Switzerland Confirms AI-Assisted Cyberattacks Breached Critical Infrastructure Operators](https://thehackernews.com/2026/11/switzerland-confirms-ai-assisted.html)

**Evidence to request:** Containment responsibilities, retained logs and the most recent response exercise.

**Decision trigger:** If an exercise exposes an ownership or evidence gap, assign a response-plan correction and retest it.

**Reference controls:** ISO/IEC 27001:2022 A.5.24 (incident management planning and preparation), A.5.26 (response to information security incidents); NIST CSF 2.0 RS.MA (incident management), RS.MI (incident mitigation)

### Google and Okta credentials targeted by phishing campaign

**Review priority:** Medium · Access management · Owner: Identity and access owner

**Why it matters:** An ongoing phishing campaign stealing corporate Google and Okta credentials means identity and access owners must verify authentication coverage and session revocation controls resist credential theft. The accountable owner should confirm access scope and permission-test results for affected identity providers.

**Source evidence:** “An ongoing phishing campaign dubbed "GoodGuys" impersonates major brands, including Google, Nvidia, Accenture, and SpaceX, to steal corporate Google and Okta credentials using fake invitations to paid expert interviews and webinars…” [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### Gmail messages stolen via malicious Chrome extension

**Review priority:** Medium · Data protection · Owner: Data and privacy owners

**Why it matters:** Theft of Gmail messages through a malicious Chrome extension requires data and privacy owners to assess whether sensitive data in email is exposed by browser extension risks. The accountable owner should review data inventory, access restrictions, and audit logs for email services.

**Source evidence:** “The Remus infostealer is stealing Gmail messages through a stealthy malicious Chrome extension, a capability the malware operators marketed as a zero-day exploit in Google's email service…” [Remus malware steals Gmail messages via fake Google Sheets extension](https://www.bleepingcomputer.com/news/security/remus-malware-steals-gmail-messages-via-fake-google-sheets-extension/)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

## Source Highlights

- [New NFS2ROOT Linux flaw can let attackers gain root privileges](https://www.bleepingcomputer.com/news/security/new-nfs2root-linux-flaw-can-let-attackers-gain-root-privileges/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-0f84e2352a98)
- [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-61e3be14c2b6)
- [Hackers Exploit 10 Vulnerabilities Across Mitel, Juniper, Vates, and Danfoss Products](https://thehackernews.com/2026/11/hackers-exploit-10-vulnerabilities.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-451f3a785e32)
- [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-27873297949c)
- [Switzerland Confirms AI-Assisted Cyberattacks Breached Critical Infrastructure Operators](https://thehackernews.com/2026/11/switzerland-confirms-ai-assisted.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-979e934b3729)
- [Unpatched Cacti Zero-Day Enables RCE in Just Four HTTP Requests via Guest Access](https://thehackernews.com/2026/11/unpatched-cacti-zero-day-enables-rce-in.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-27f1645ed04a)
- [OpenAI warns GPT-6.2 Astra will hit usage limits 40% faster because it fixed a bug](https://www.bleepingcomputer.com/news/artificial-intelligence/openai-warns-gpt-62-astra-will-hit-usage-limits-40-percent-faster-because-it-fixed-a-bug/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-ac6c22bfffe5)
- [ThreatsDay: 10M NGINX Services at Risk, 250+ Malicious Extensions, AI Server Hijacking + 17 More Stories](https://thehackernews.com/2026/11/threatsday-250-rogue-extensions-10m.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-0b75246ced86)
- [NordVPN Black Friday Deal: Get 78% off VPN plans in 2026](https://www.bleepingcomputer.com/news/security/nordvpn-black-friday-deal-get-78-percent-off-vpn-plans-in-2026/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-0bd18f3d2e78)
- [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-deebe28bb42d)
- [Remus malware steals Gmail messages via fake Google Sheets extension](https://www.bleepingcomputer.com/news/security/remus-malware-steals-gmail-messages-via-fake-google-sheets-extension/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-57d73d788295)
- [North Korea-Linked PolinRider Poisons Over 7,600 GitHub Repositories to Spread Malware](https://thehackernews.com/2026/11/north-korea-linked-polinrider-poisons.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-27/#reporting-0574110d7d17)
