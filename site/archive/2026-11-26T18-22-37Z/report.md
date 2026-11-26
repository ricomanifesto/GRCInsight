# GRC Intelligence Report - 2026-11-26
**Generated:** 2026-11-26T18:22:37.411163Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/7eb4ba5194d1c59e1a9ddf7f772bdb228f1222b6/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-26](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 29
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Active exploitation of highly critical vulnerabilities in Drupal core, Mitel MiCollab, and GeoServer has been confirmed, with CISA adding ten flaws to its Known Exploited Vulnerabilities catalog. These developments demand immediate asset identification and patching across widely deployed content management, collaboration, and geospatial platforms. Vulnerability and asset owners must verify affected versions are inventoried and remediated to maintain control assurance. [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html); [Hackers Exploit 10 Vulnerabilities Across Mitel, Juniper, Vates, and Danfoss Products](https://thehackernews.com/2026/11/hackers-exploit-10-vulnerabilities.html); [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html)

Simultaneously, a sophisticated phishing campaign impersonating major brands steals corporate Google and Okta credentials, while North Korean actors poison thousands of GitHub repositories and a password manager suffers a backend breach via GitHub compromise. These identity and supply chain attacks bypass traditional controls and concentrate risk in trusted dependencies. Identity and access owners should review authentication coverage, and supplier risk owners must assess third-party assurance evidence. [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/); [North Korea-Linked PolinRider Poisons Over 7,600 GitHub Repositories to Spread Malware](https://thehackernews.com/2026/11/north-korea-linked-polinrider-poisons.html); [1Password Hacked, Customer Data and Source Code Stolen in GitHub Account Breach](https://thehackernews.com/2026/11/1password-hacked-customer-data-and.html)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Drupal core exposes site takeover under active exploitation

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of a highly critical Drupal vulnerability requires immediate asset identification and patching to prevent site takeover. Vulnerability and asset owners should confirm affected Drupal installations are inventoried and remediated.

**Source evidence:** “Drupal has warned of a new "highly critical" security flaw impacting Drupal core that it said has been exploited in the wild. The vulnerability, tracked as CVE-2026-136716 &#40;CVSS score: N/A&#41;, has been described as a case of improper checking for unusual or exceptional conditions. It also relates to CVE-2026-132165 aka Fail2Install in that it addresses remaining vulnerable installation states…” [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Mitel MiCollab joins CISA KEV catalog with active exploitation

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** CISA KEV inclusion mandates federal agencies and signals critical risk for all organizations using Mitel MiCollab. Vulnerability and asset owners should verify Mitel MiCollab deployments and apply vendor patches.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Wednesday added 10 security flaws to its Known Exploited Vulnerabilities &#40;KEV&#41; catalog, including five vulnerabilities impacting Mitel MiCollab that were disclosed last week. The Mitel MiCollab vulnerabilities are listed below - CVE-2026-133275 &#40;CVSS score: 5.3&#41; - An arbitrary file upload vulnerability in the Audio, Web and…” [Hackers Exploit 10 Vulnerabilities Across Mitel, Juniper, Vates, and Danfoss Products](https://thehackernews.com/2026/11/hackers-exploit-10-vulnerabilities.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### GeoServer faces active exploitation of unauthenticated RCE chains

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of high-severity GeoServer flaws demands immediate patching of internet-facing instances. Vulnerability and asset owners should confirm GeoServer versions and apply vendor patches.

**Source evidence:** “Threat actors are actively exploiting two newly patched security flaws in GeoServer, according to watchTowr. The vulnerabilities in question are CVE-2026-120705 and CVE-2026-129243, details of which are below - CVE-2026-120705 &#40;CVSS score: 8.6&#41; - An arbitrary file read vulnerability that could enable an attacker to access local text files readable by the GeoServer process or fetch…” [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Corporate Google and Okta credentials targeted by GoodGuys phishing

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** Credential theft via sophisticated brand impersonation bypasses email controls and threatens identity systems. Identity and access owners should review authentication coverage and session revocation for Google and Okta.

**Source evidence:** “An ongoing phishing campaign dubbed "GoodGuys" impersonates major brands, including Google, Nvidia, Accenture, and SpaceX, to steal corporate Google and Okta credentials using fake invitations to paid expert interviews and webinars…” [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### GitHub repositories poisoned with Python loader in supply chain attack

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Long-running supply chain compromise of open-source repositories undermines software integrity assumptions. Supplier risk owners should review dependency scanning and verify provenance of Python packages.

**Source evidence:** “The threat actors behind the PolinRider campaign have been observed planting a Python loader in GitHub repositories, as evidence emerges that the activity may have started as far back as February 2025. "The loader hides in a small utils package or in conftest.py," SafeDep said in a report published this week. "When Python imports the file, the loader reads the newest transaction that an…” [North Korea-Linked PolinRider Poisons Over 7,600 GitHub Repositories to Spread Malware](https://thehackernews.com/2026/11/north-korea-linked-polinrider-poisons.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### 1Password backend systems breached via GitHub account compromise

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Compromise of a password manager's backend via supply chain highlights third-party risk concentration. Supplier risk owners should assess 1Password assurance evidence and verify vault isolation claims.

**Source evidence:** “Popular password management software 1Password on Wednesday disclosed a security incident involving its backend systems that led to the unauthorized access of some customer information, but emphasized that customer password vaults and other secrets were not accessed. "While we took immediate steps to contain the incident, the attacker gained access to some of our backend systems and accessed a…” [1Password Hacked, Customer Data and Source Code Stolen in GitHub Account Breach](https://thehackernews.com/2026/11/1password-hacked-customer-data-and.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

## Source Highlights

- [Drupal Warns of New Highly Critical Site Takeover Vulnerability Under Active Exploitation](https://thehackernews.com/2026/11/drupal-warns-of-new-highly-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-61e3be14c2b6)
- [Hackers Exploit 10 Vulnerabilities Across Mitel, Juniper, Vates, and Danfoss Products](https://thehackernews.com/2026/11/hackers-exploit-10-vulnerabilities.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-451f3a785e32)
- [Hackers Exploit Two GeoServer Flaws as Researchers Warn of Unauthenticated RCE Chains](https://thehackernews.com/2026/11/hackers-exploit-two-geoserver-flaws-as.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-27873297949c)
- [NordVPN Black Friday Deal: Get 78% off VPN plans in 2026](https://www.bleepingcomputer.com/news/security/nordvpn-black-friday-deal-get-78-percent-off-vpn-plans-in-2026/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-0bd18f3d2e78)
- [Fake paid expert interviews impersonate brands to steal Google logins](https://www.bleepingcomputer.com/news/apple/fake-paid-expert-interviews-impersonate-brands-to-steal-google-logins/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-deebe28bb42d)
- [Remus malware steals Gmail messages via fake Google Sheets extension](https://www.bleepingcomputer.com/news/security/remus-malware-steals-gmail-messages-via-fake-google-sheets-extension/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-57d73d788295)
- [North Korea-Linked PolinRider Poisons Over 7,600 GitHub Repositories to Spread Malware](https://thehackernews.com/2026/11/north-korea-linked-polinrider-poisons.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-0574110d7d17)
- [SYS010 malware abuses browser management to spy on Gmail, Outlook](https://www.bleepingcomputer.com/news/security/sys010-malware-abuses-browser-management-to-spy-on-gmail-outlook/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-34599e7b6c56)
- [Most Wanted: The Phishing Kits and Techniques Getting Past Security Controls](https://thehackernews.com/2026/11/most-wanted-phishing-kits-and.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-54cc21ceab24)
- [1Password Hacked, Customer Data and Source Code Stolen in GitHub Account Breach](https://thehackernews.com/2026/11/1password-hacked-customer-data-and.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-5e5b0d3bb248)
- [Cyprus Becomes Espionage Target for Iranian Hackers](https://www.darkreading.com/cyberattacks-data-breaches/cyprus-espionage-target-iranian-hackers) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-9bbd9ec06777)
- [13 Malicious NuGet Packages Turn Fake .NET Job Assessments Into Malware Delivery Traps](https://thehackernews.com/2026/11/13-malicious-nuget-packages-turn-fake.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-26/#reporting-8720d53f4644)
