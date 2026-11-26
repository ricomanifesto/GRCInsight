# GRC Intelligence Report - 2026-11-26
**Generated:** 2026-11-26T21:16:53.129084Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/0af84ca5c8721ec500e5e041e4102a69c01f0618/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-26](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Active exploitation of highly critical vulnerabilities in Drupal core and GeoServer, alongside CISA's addition of ten flaws to the Known Exploited Vulnerabilities catalog including Mitel MiCollab, signals an elevated tempo of weaponized vulnerability exploitation against widely deployed platforms. Control owners must verify that asset inventories capture affected products and that remediation or compensating controls are validated with version evidence. [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html); [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html)

Simultaneous identity-focused campaigns — including the GoodGuys phishing operation harvesting corporate Google and Okta credentials, North Korea-linked PolinRider poisoning over 7,600 GitHub repositories, and the 1Password backend breach exposing customer information — extend risk beyond perimeter defenses into trusted software supply chains and identity providers. Access management and third-party risk owners should confirm authentication coverage against brand-impersonation lures and review supplier dependencies on compromised repositories. [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/); [North Korea-Linked PolinRider Poisons Over 7,600 GitHub Repositories to Spread Malware](https://thehackernews.com/2026/11/north-korea-linked-polinrider-poisons.html); [1Password Hacked, Customer Data and Source Code Stolen in GitHub Account Breach](https://thehackernews.com/2026/11/1password-hacked-customer-data-and.html)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Drupal core exposes site takeover under active exploitation

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a highly critical Drupal core flaw weakens assurance that web platforms are patched against known threats. Vulnerability and asset owners should confirm whether deployed Drupal instances meet the exposure conditions and verify remediation status with installed version evidence.

**Source evidence:** “Drupal has warned of a new "highly critical" security flaw impacting Drupal core that it said has been exploited in the wild. The vulnerability, tracked as CVE-2026-136716 &#40;CVSS score: N/A&#41;, has been described as a case of improper checking for unusual or exceptional conditions. It also relates to CVE-2026-132165 aka Fail2Install in that it addresses remaining vulnerable installation states” [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### GeoServer flaws enable active exploitation of arbitrary file read

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of GeoServer arbitrary file read vulnerabilities weakens patch management assurance for geospatial infrastructure. Vulnerability and asset owners should confirm whether deployed GeoServer instances are patched and verify compensating controls for unpatched assets.

**Source evidence:** “Threat actors are actively exploiting two newly patched security flaws in GeoServer, according to watchTowr. The vulnerabilities in question are CVE-2026-120705 and CVE-2026-129243, details of which are below - CVE-2026-120705 &#40;CVSS score: 8.6&#41; - An arbitrary file read vulnerability that could enable an attacker to access local text files readable by the GeoServer process or fetch” [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### GoodGuys phishing campaign steals corporate Google and Okta credentials

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** An active phishing campaign bypassing brand trust to harvest corporate identity credentials weakens access boundary assurance. Identity and access owners should confirm whether authentication coverage and account revocation controls detect credential theft from brand-impersonation lures.

**Source evidence:** “An ongoing phishing campaign dubbed "GoodGuys" impersonates major brands, including Google, Nvidia, Accenture, and SpaceX, to steal corporate Google and Okta credentials using fake invitations to paid expert interviews and webinars” [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### PolinRider campaign poisons GitHub repositories with Python loader

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Nation-state-linked repository poisoning across thousands of GitHub projects weakens software supply chain assurance. Supplier risk owners should confirm whether internal builds depend on compromised repositories and review supplier remediation assurance evidence.

**Source evidence:** “The threat actors behind the PolinRider campaign have been observed planting a Python loader in GitHub repositories, as evidence emerges that the activity may have started as far back as February 2025. "The loader hides in a small utils package or in conftest.py," SafeDep said in a report published this week.” [North Korea-Linked PolinRider Poisons Over 7,600 GitHub Repositories to Spread Malware](https://thehackernews.com/2026/11/north-korea-linked-polinrider-poisons.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### 1Password backend systems breach exposes customer information

**Review priority:** High · Data protection · Owner: Data and privacy owners

**Why it matters:** A password manager's backend compromise exposing customer data weakens trust in credential storage assurances. Data and privacy owners should confirm whether the accessed customer information includes sensitive identifiers and review the supplier's containment evidence.

**Source evidence:** “Popular password management software 1Password on Wednesday disclosed a security incident involving its backend systems that led to the unauthorized access of some customer information, but emphasized that customer password vaults and other secrets were not accessed. "While we took immediate steps to contain the incident, the attacker gained access to some of our backend systems and accessed a” [1Password Hacked, Customer Data and Source Code Stolen in GitHub Account Breach](https://thehackernews.com/2026/11/1password-hacked-customer-data-and.html)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### Phishing kits bypass email security web filtering and safe browsing

**Review priority:** Medium · Monitoring and detection · Owner: Detection and monitoring owner

**Why it matters:** Measured breakthrough rates showing phishing kits evading layered defenses weaken detection coverage assurance. Detection and monitoring owners should confirm whether telemetry distinguishes breakthrough attacks from expected traffic and review alert routing for high-breakthrough kits.

**Source evidence:** “Every phishing attack has to get past email security, web filtering, and safe browsing before it reaches an employee. Some kits manage that far more often than others, and those are the kits that security teams need to know about. At Push Security, we measure this as breakthrough rate: The share of attacks that get past email security, web gateways, and safe browsing to reach the user.” [Most Wanted: The Phishing Kits and Techniques Getting Past Security Controls](https://thehackernews.com/2026/11/most-wanted-phishing-kits-and.html)

**Evidence to request:** Log coverage, a detection test, alert routing and investigation ownership.

**Decision trigger:** If a detection test fails, assign the coverage or routing correction and repeat the test.

**Reference controls:** ISO/IEC 27001:2022 A.8.15 (logging), A.8.16 (monitoring activities); NIST CSF 2.0 DE.CM (continuous monitoring), DE.AE (adverse event analysis)

## Source Highlights

- [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-61e3be14c2b6)
- [Hackers Exploit 10 Vulnerabilities Across Mitel, Juniper, Vates, and Danfoss Products](https://thehackernews.com/2026/11/hackers-exploit-10-vulnerabilities.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-451f3a785e32)
- [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-27873297949c)
- [OpenAI warns GPT-6.2 Astra will hit usage limits 40% faster because it fixed a bug](https://www.bleepingcomputer.com/news/artificial-intelligence/openai-warns-gpt-62-astra-will-hit-usage-limits-40-percent-faster-because-it-fixed-a-bug/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-ac6c22bfffe5)
- [ThreatsDay: 10M NGINX Services at Risk, 250+ Malicious Extensions, AI Server Hijacking + 17 More Stories](https://thehackernews.com/2026/11/threatsday-250-rogue-extensions-10m.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-0b75246ced86)
- [NordVPN Black Friday Deal: Get 78% off VPN plans in 2026](https://www.bleepingcomputer.com/news/security/nordvpn-black-friday-deal-get-78-percent-off-vpn-plans-in-2026/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-0bd18f3d2e78)
- [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-deebe28bb42d)
- [Remus malware steals Gmail messages via fake Google Sheets extension](https://www.bleepingcomputer.com/news/security/remus-malware-steals-gmail-messages-via-fake-google-sheets-extension/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-57d73d788295)
- [North Korea-Linked PolinRider Poisons Over 7,600 GitHub Repositories to Spread Malware](https://thehackernews.com/2026/11/north-korea-linked-polinrider-poisons.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-0574110d7d17)
- [SYS010 malware abuses browser management to spy on Gmail, Outlook](https://www.bleepingcomputer.com/news/security/sys010-malware-abuses-browser-management-to-spy-on-gmail-outlook/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-34599e7b6c56)
- [Most Wanted: The Phishing Kits and Techniques Getting Past Security Controls](https://thehackernews.com/2026/11/most-wanted-phishing-kits-and.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-54cc21ceab24)
- [1Password Hacked, Customer Data and Source Code Stolen in GitHub Account Breach](https://thehackernews.com/2026/11/1password-hacked-customer-data-and.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-5e5b0d3bb248)
