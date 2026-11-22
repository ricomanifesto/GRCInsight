# GRC Intelligence Report - 2026-11-22
**Generated:** 2026-11-22T00:36:11.498619Z
**Date of Issue:** November 2026
**Analysis Period:** November 2026
**Source:** [SentryDigest](https://raw.githubusercontent.com/ricomanifesto/SentryDigest/6bb101c014a022d79e92dfbd87db9f134059f3a5/site/feed.xml)
**Source Issue:** [SentryDigest 2026-11-22](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

CISA added four actively exploited vulnerabilities in widely deployed enterprise infrastructure — Apache Roller, Cisco Expressway, SAP NetWeaver, and VMware vCenter — to its Known Exploited Vulnerabilities catalog, while threat actors simultaneously weaponized a Cisco Expressway flaw within days of proof-of-concept release and a China-linked group exploited a VMware vCenter zero-day for administrative access. These developments compress remediation windows for critical assets and demand immediate asset inventory, patch verification, and lateral movement assessment. [Hackers Exploit Critical VMware, Cisco, and Apache Flaws as Espionage Attacks Emerge](https://thehackernews.com/2026/11/hackers-exploit-critical-vmware-cisco.html); [Hackers Exploit Critical Cisco Expressway Flaw, Breach Four Devices and Reach Internal Network](https://thehackernews.com/2026/11/hackers-exploit-critical-cisco.html); [China-Linked Hackers Exploit Critical VMware vCenter Zero-Day to Gain Admin Access and Steal Data](https://thehackernews.com/2026/11/china-linked-hackers-exploit-critical.html)

Cloud and identity supply chain risks materialized through a Rackspace Spot credential compromise exposing customer Kubernetes secrets, a Microsoft Entra Connect Health breach revealing administrator emails and tenant configuration, and a Linux KVM hypervisor flaw enabling cross-VM memory reading on AMD hosts. Control owners must validate third-party access scopes, rotate compromised secrets, audit identity synchronization permissions, and confirm hypervisor patch deployment on affected hardware configurations. [Rackspace Spot breach let hackers access customer Kubernetes secrets](https://www.bleepingcomputer.com/news/security/rackspace-spot-breach-let-hackers-access-customer-kubernetes-secrets/); [Microsoft Entra Connect Health flaw exploited to steal tenant data](https://www.bleepingcomputer.com/news/security/microsoft-entra-connect-health-flaw-exploited-to-steal-tenant-data/); [Linux KVM Flaw CVE-2026-99312 Lets Guest VMs Access Host Memory on AMD Hosts](https://thehackernews.com/2026/11/new-linux-kvm-flaw-cve-2026-99312-lets.html)

Scope: 6 findings and 0 sourced regulatory changes from 12 retained sources. Review priorities rank what to check first; confirm whether each finding applies to your organization before assigning work.

## Sourced Regulatory Changes

No sourced regulatory changes identified in the supplied evidence.

## Evidence and Decisions

Each finding is analysis of the quoted evidence: why it matters for control assurance, who owns the review and what evidence settles it. Reference controls are review aids, not a compliance determination.

### Apache Roller, Cisco Expressway, SAP NetWeaver, and Broadcom VMware vCenter added to CISA KEV with active exploitation

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** CISA KEV inclusion signals confirmed exploitation requiring immediate remediation. Vulnerability and asset owners must identify affected deployments, verify patch status, and document compensating controls for any unpatched instances.

**Source evidence:** “The U.S. Cybersecurity and Infrastructure Security Agency &#40;CISA&#41; on Friday added four flaws impacting Apache Roller, Cisco Expressway, SAP NetWeaver, and Broadcom VMware vCenter to its Known Exploited Vulnerabilities &#40;KEV&#41;, citing evidence of active exploitation. The vulnerabilities are listed below - CVE-2026-129448 &#40;CVSS score: 9.8&#41; - A deserialization of untrusted data vulnerability in…” [Hackers Exploit Critical VMware, Cisco, and Apache Flaws as Espionage Attacks Emerge](https://thehackernews.com/2026/11/hackers-exploit-critical-vmware-cisco.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Cisco Expressway exploited in the wild after PoC release

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Rapid weaponization after PoC publication reduces remediation windows. Vulnerability and asset owners must confirm Cisco Expressway patch deployment and validate network segmentation limits exposure to unauthenticated remote attackers.

**Source evidence:** “Threat actors have been observed exploiting a recently disclosed critical security flaw in Cisco Expressway to breach a Russian organization shortly after the public release of a proof-of-concept &#40;PoC&#41; exploit. The activity involves the exploitation of CVE-2026-76466 &#40;CVSS score: 9.8&#41;, a vulnerability that could allow an unauthenticated, remote attacker with network access to a Cisco Expressway…” [Hackers Exploit Critical Cisco Expressway Flaw, Breach Four Devices and Reach Internal Network](https://thehackernews.com/2026/11/hackers-exploit-critical-cisco.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### VMware vCenter Server zero-day exploited by China-linked group for unauthorized admin access

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Zero-day exploitation of central virtualization management platform enables persistent administrative access. Vulnerability and asset owners must verify emergency patch deployment, review vCenter administrative accounts for anomalies, and assess lateral movement risk.

**Source evidence:** “The suspected China-nexus cyber espionage group known as Armory Castle &#40;formerly UNC5221&#41; has been attributed to the zero-day exploitation of a critical security flaw in VMware vCenter Server in early September 2026. The vulnerability, tracked as CVE-2026-123890 &#40;CVSS score: 9.8&#41;, is a case of authentication bypass in the VMware Directory Service that could be exploited to gain unauthorized…” [China-Linked Hackers Exploit Critical VMware vCenter Zero-Day to Gain Admin Access and Steal Data](https://thehackernews.com/2026/11/china-linked-hackers-exploit-critical.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

### Rackspace Spot cloud platform breached via compromised credentials exposing customer Kubernetes secrets

**Review priority:** High · Third-party risk · Owner: Supplier risk owner

**Why it matters:** Supplier credential compromise led to unauthorized workload deployment and secret access in tenant environments. Supplier risk owners must review Rackspace Spot access scope, demand breach impact assessments, and verify secret rotation and Kubernetes RBAC configurations.

**Source evidence:** “Rackspace warned customers that hackers breached its Rackspace Spot cloud platform using compromised credentials, allowing them to deploy unauthorized workloads and access Kubernetes secrets in customer clusters…” [Rackspace Spot breach let hackers access customer Kubernetes secrets](https://www.bleepingcomputer.com/news/security/rackspace-spot-breach-let-hackers-access-customer-kubernetes-secrets/)

**Evidence to request:** Supplier access scope, control responsibilities and evidence of remediation assurance.

**Decision trigger:** If the supplier dependency exists and assurance is insufficient, request evidence or escalate the assurance gap to its owner.

**Reference controls:** ISO/IEC 27001:2022 A.5.19 (supplier relationships), A.5.21 (ICT supply chain), A.5.22 (monitoring and review of supplier services); NIST CSF 2.0 GV.SC (cybersecurity supply chain risk management)

### Entra Connect Health service vulnerability exploited to access administrator emails and tenant configuration

**Review priority:** High · Access management · Owner: Identity and access owner

**Why it matters:** Identity synchronization service breach exposes privileged administrator identities and tenant metadata. Identity and access owners must audit Entra Connect Health permissions, review administrator account access logs, and validate conditional access policies for sync service accounts.

**Source evidence:** “Microsoft is warning organizations that it suffered a data breach after attackers exploited a vulnerability in its Entra Connect Health service to gain unauthorized access to administrator email addresses and tenant configuration information…” [Microsoft Entra Connect Health flaw exploited to steal tenant data](https://www.bleepingcomputer.com/news/security/microsoft-entra-connect-health-flaw-exploited-to-steal-tenant-data/)

**Evidence to request:** Access scope, authentication coverage, session revocation and a permission-test result.

**Decision trigger:** If a permission gap is reproduced, assign a control correction and verify it; otherwise retain the test evidence.

**Reference controls:** ISO/IEC 27001:2022 A.5.15 (access control), A.5.18 (access rights), A.8.2 (privileged access rights); NIST CSF 2.0 PR.AA (identity management, authentication and access control)

### KVM hypervisor flaw allows cross-VM memory access on AMD hosts with nested virtualization

**Review priority:** High · Vulnerability management · Owner: Vulnerability and asset owners

**Why it matters:** Hypervisor memory isolation failure threatens multi-tenant cloud confidentiality. Vulnerability and asset owners must inventory AMD-based hosts with nested virtualization, apply kernel updates, and assess data exposure risk for workloads on affected infrastructure.

**Source evidence:** “A flaw in KVM, the hypervisor built into the Linux kernel, let researchers read about 127 GB of a cloud server's memory from inside a virtual machine of their own on DigitalOcean. On a shared server, that memory can include other customers' virtual machines. The flaw, tracked as CVE-2026-99312, affects only hosts with AMD processors and nested virtualization enabled. Fixed kernels shipped…” [Linux KVM Flaw CVE-2026-99312 Lets Guest VMs Access Host Memory on AMD Hosts](https://thehackernews.com/2026/11/new-linux-kvm-flaw-cve-2026-99312-lets.html)

**Evidence to request:** Affected-asset inventory, installed versions, remediation status and an exception owner.

**Decision trigger:** If applicability is confirmed, decide on remediation or a documented exception; otherwise record why the finding does not apply.

**Reference controls:** ISO/IEC 27001:2022 A.8.8 (management of technical vulnerabilities); NIST CSF 2.0 ID.RA (risk assessment), PR.PS (platform security)

## Source Highlights

- [GnuPG Warns Critical GPGME Flaw Could Expose App Data via Malicious OpenPGP Keys](https://thehackernews.com/2026/11/gnupg-warns-critical-gpgme-flaw-could.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-3b426a1ae487)
- [Hackers Exploit Critical VMware, Cisco, and Apache Flaws as Espionage Attacks Emerge](https://thehackernews.com/2026/11/hackers-exploit-critical-vmware-cisco.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-552b60cb29a0)
- [WhatsApp Patches 3 Security Flaws, Including Android Bug Suspected of Use in Scams](https://thehackernews.com/2026/11/whatsapp-patches-3-security-flaws.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-b44c0a854e15)
- [Linux KVM Flaw CVE-2026-99312 Lets Guest VMs Access Host Memory on AMD Hosts](https://thehackernews.com/2026/11/new-linux-kvm-flaw-cve-2026-99312-lets.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-c7b209f2aed8)
- [Hackers Exploit Critical Cisco Expressway Flaw, Breach Four Devices and Reach Internal Network](https://thehackernews.com/2026/11/hackers-exploit-critical-cisco.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-c99f552cbbef)
- [China-Linked Hackers Exploit Critical VMware vCenter Zero-Day to Gain Admin Access and Steal Data](https://thehackernews.com/2026/11/china-linked-hackers-exploit-critical.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-209921156d98)
- [Rackspace Spot breach let hackers access customer Kubernetes secrets](https://www.bleepingcomputer.com/news/security/rackspace-spot-breach-let-hackers-access-customer-kubernetes-secrets/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-1fa3870c33e2)
- [Microsoft Entra Connect Health flaw exploited to steal tenant data](https://www.bleepingcomputer.com/news/security/microsoft-entra-connect-health-flaw-exploited-to-steal-tenant-data/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-cd00c38abb0c)
- [BADBOX botnet returns with record-breaking 40 billion daily ad requests](https://www.bleepingcomputer.com/news/security/badbox-30-botnet-returns-with-record-breaking-40-billion-daily-ad-requests/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-9c3f2473640f)
- [FBI reportedly hacked again, this time targeting nationwide police database](https://www.bleepingcomputer.com/news/security/fbi-reportedly-hacked-again-this-time-targeting-nationwide-police-database/) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-6eaabec12846)
- [A Single Malicious Webpage Let Researchers Hijack Meta Muse and Access Private Chats](https://thehackernews.com/2026/11/a-single-malicious-webpage-let.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-059e30cfca73)
- [Attackers' AI Agents Found a Zero-Day in Medical-Imaging Software and Gained Root Access](https://thehackernews.com/2026/11/attackers-ai-agents-found-zero-day-in.html) · [View in SentryDigest](https://sentrydigest.ricomanifesto.com/archive/2026-11-22/#reporting-31de93106fde)
