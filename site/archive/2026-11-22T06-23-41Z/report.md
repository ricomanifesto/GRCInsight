# GRC Intelligence Report - 2026-11-22
**Generated:** 2026-11-22T06:23:41.224898Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/3737cfdb5dbec841762a9bc258b76e872556c02f/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-22](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Multiple critical infrastructure vulnerabilities are under active exploitation, with CISA adding four flaws to its Known Exploited Vulnerabilities catalog and a China-linked group leveraging a VMware vCenter zero-day for administrative access. Simultaneously, cloud hypervisor and supplier breaches demonstrate cross-tenant data exposure and credential compromise risks that bypass traditional perimeter controls. These developments collectively weaken vulnerability management, data protection, and third-party risk assurances across cloud and identity infrastructure. [Hackers Exploit Critical VMware, Cisco, and Apache Flaws as Espionage Attacks Emerge](https://thehackernews.com/2026/11/hackers-exploit-critical-vmware-cisco.html); [Linux KVM Flaw CVE-2026-99312 Lets Guest VMs Access Host Memory on AMD Hosts](https://thehackernews.com/2026/11/new-linux-kvm-flaw-cve-2026-99312-lets.html); [China-Linked Hackers Exploit Critical VMware vCenter Zero-Day to Gain Admin Access and Steal Data](https://thehackernews.com/2026/11/china-linked-hackers-exploit-critical.html); [Rackspace Spot breach let hackers access customer Kubernetes secrets](https://www.bleepingcomputer.com/news/security/rackspace-spot-breach-let-hackers-access-customer-kubernetes-secrets/); [Microsoft Entra Connect Health flaw exploited to steal tenant data](https://www.bleepingcomputer.com/news/security/microsoft-entra-connect-health-flaw-exploited-to-steal-tenant-data/)

AI supply chain integrity is also compromised, as three inference providers suffered months of undetected prompt theft despite Zero Data Retention settings, and a widely used cryptographic library contains a critical memory flaw affecting all downstream applications. Control owners should prioritize emergency patching of KEV-listed assets, verify hypervisor isolation in shared environments, review supplier access scopes for cloud and AI services, and confirm cryptographic library versions across the software supply chain. [OpenRouter Drops 3 Providers After Researchers Catch Months of Prompt Theft at AI Hosting Firms](https://thehackernews.com/2026/11/openrouter-drops-3-providers-after.html)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### CISA Known Exploited Vulnerabilities adds four actively exploited flaws

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Active exploitation of critical infrastructure components requires immediate asset identification and remediation verification. Vulnerability and asset owners should confirm affected product versions are inventoried and patched or compensated.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Friday added four flaws impacting Apache Roller, Cisco Expressway, SAP NetWeaver, and Broadcom VMware vCenter to its Known Exploited Vulnerabilities &#40;KEV&#41;, citing evidence of active exploitation. The vulnerabilities are listed below - CVE-2026-129448 &#40;CVSS score: 9.8&#41; - A deserialization of untrusted data vulnerability in…” [Hackers Exploit Critical VMware, Cisco, and Apache Flaws as Espionage Attacks Emerge](https://thehackernews.com/2026/11/hackers-exploit-critical-vmware-cisco.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Linux KVM hypervisor on AMD hosts exposes cross-tenant memory

**Review priority:** High · Data protection · Owner: Data and privacy owners

**Why it matters:** Cross-tenant memory exposure in shared cloud environments undermines data isolation assurances. Data and privacy owners should verify hypervisor patching status and nested virtualization configurations with cloud providers.

**Source evidence:** “A flaw in KVM, the hypervisor built into the Linux kernel, let researchers read about 127 GB of a cloud server's memory from inside a virtual machine of their own on DigitalOcean. On a shared server, that memory can include other customers' virtual machines. The flaw, tracked as CVE-2026-99312, affects only hosts with AMD processors and nested virtualization enabled.” [Linux KVM Flaw CVE-2026-99312 Lets Guest VMs Access Host Memory on AMD Hosts](https://thehackernews.com/2026/11/new-linux-kvm-flaw-cve-2026-99312-lets.html)

**Evidence to request:** Data inventory, access restrictions, audit logs and a documented exposure assessment.

**Decision trigger:** If relevant data is exposed to the reported access path, decide which protection or access change is needed.

**Reference controls:** ISO/IEC 27001:2022 A.5.34 (privacy and protection of PII), A.8.12 (data leakage prevention), A.8.24 (use of cryptography); NIST CSF 2.0 PR.DS (data security)

### VMware vCenter Server authentication bypass exploited by espionage group

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Zero-day exploitation of central management infrastructure enables persistent administrative access. Vulnerability and asset owners should confirm emergency patching of vCenter Server and review administrative access logs for anomalies.

**Source evidence:** “The suspected China-nexus cyber espionage group known as Armory Castle &#40;formerly UNC5221&#41; has been attributed to the zero-day exploitation of a critical security flaw in VMware vCenter Server in early September 2026. The vulnerability, tracked as CVE-2026-123890 &#40;CVSS score: 9.8&#41;, is a case of authentication bypass in the VMware Directory Service that could be exploited to gain unauthorized…” [China-Linked Hackers Exploit Critical VMware vCenter Zero-Day to Gain Admin Access and Steal Data](https://thehackernews.com/2026/11/china-linked-hackers-exploit-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Rackspace Spot cloud platform breach exposes Kubernetes secrets

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Compromised supplier credentials leading to customer secret exposure indicates insufficient identity segmentation. Supplier risk owners should review Rackspace access scopes, credential rotation practices, and contractual assurance for secret protection.

**Source evidence:** “Rackspace warned customers that hackers breached its Rackspace Spot cloud platform using compromised credentials, allowing them to deploy unauthorized workloads and access Kubernetes secrets in customer clusters…” [Rackspace Spot breach let hackers access customer Kubernetes secrets](https://www.bleepingcomputer.com/news/security/rackspace-spot-breach-let-hackers-access-customer-kubernetes-secrets/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Microsoft Entra Connect Health service breach exposes tenant data

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** Breach of identity hygiene tooling compromises administrative visibility and tenant trust. Identity and access owners should verify Entra Connect Health deployment scope, monitor for anomalous administrator activity, and assess configuration drift.

**Source evidence:** “Microsoft is warning organizations that it suffered a data breach after attackers exploited a vulnerability in its Entra Connect Health service to gain unauthorized access to administrator email addresses and tenant configuration information…” [Microsoft Entra Connect Health flaw exploited to steal tenant data](https://www.bleepingcomputer.com/news/security/microsoft-entra-connect-health-flaw-exploited-to-steal-tenant-data/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### AI inference providers via OpenRouter suffer undetected prompt theft

**Review priority:** Medium · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Extended undetected data exfiltration from AI supply chain violates retention commitments. Supplier risk owners should inventory AI provider dependencies, validate data retention controls, and request incident evidence from OpenRouter.

**Source evidence:** “Attackers stole data from inside three AI inference providers for months, and none of the three knew until researchers told them, the industrial cybersecurity company Dragos said this week. Some of the stolen requests were flagged as Zero Data Retention, the setting that is supposed to mean a prompt is never stored.” [OpenRouter Drops 3 Providers After Researchers Catch Months of Prompt Theft at AI Hosting Firms](https://thehackernews.com/2026/11/openrouter-drops-3-providers-after.html)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

## Source Highlights

- [GnuPG Warns Critical GPGME Flaw Could Expose App Data via Malicious OpenPGP Keys](https://thehackernews.com/2026/11/gnupg-warns-critical-gpgme-flaw-could.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-3b426a1ae487)
- [Hackers Exploit Critical VMware, Cisco, and Apache Flaws as Espionage Attacks Emerge](https://thehackernews.com/2026/11/hackers-exploit-critical-vmware-cisco.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-552b60cb29a0)
- [WhatsApp Patches 3 Security Flaws, Including Android Bug Suspected of Use in Scams](https://thehackernews.com/2026/11/whatsapp-patches-3-security-flaws.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-b44c0a854e15)
- [Linux KVM Flaw CVE-2026-99312 Lets Guest VMs Access Host Memory on AMD Hosts](https://thehackernews.com/2026/11/new-linux-kvm-flaw-cve-2026-99312-lets.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-c7b209f2aed8)
- [Hackers Exploit Critical Cisco Expressway Flaw, Breach Four Devices and Reach Internal Network](https://thehackernews.com/2026/11/hackers-exploit-critical-cisco.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-c99f552cbbef)
- [China-Linked Hackers Exploit Critical VMware vCenter Zero-Day to Gain Admin Access and Steal Data](https://thehackernews.com/2026/11/china-linked-hackers-exploit-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-209921156d98)
- [OpenRouter Drops 3 Providers After Researchers Catch Months of Prompt Theft at AI Hosting Firms](https://thehackernews.com/2026/11/openrouter-drops-3-providers-after.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-6d087c898942)
- [Researchers Demonstrate Ghostscript Sandbox-Escape RCE via Crafted File Uploads in Popular Apps](https://thehackernews.com/2026/11/researchers-demonstrate-ghostscript.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-a3c63e958cb9)
- [Rackspace Spot breach let hackers access customer Kubernetes secrets](https://www.bleepingcomputer.com/news/security/rackspace-spot-breach-let-hackers-access-customer-kubernetes-secrets/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-1fa3870c33e2)
- [Microsoft Entra Connect Health flaw exploited to steal tenant data](https://www.bleepingcomputer.com/news/security/microsoft-entra-connect-health-flaw-exploited-to-steal-tenant-data/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-cd00c38abb0c)
- [BADBOX botnet returns with record-breaking 40 billion daily ad requests](https://www.bleepingcomputer.com/news/security/badbox-30-botnet-returns-with-record-breaking-40-billion-daily-ad-requests/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-9c3f2473640f)
- [FBI reportedly hacked again, this time targeting nationwide police database](https://www.bleepingcomputer.com/news/security/fbi-reportedly-hacked-again-this-time-targeting-nationwide-police-database/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-6eaabec12846)
