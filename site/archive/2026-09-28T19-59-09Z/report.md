# GRC Intelligence Report - 2026-09-28
**Generated:** 2026-09-28T19:59:09.716174Z
**Date of Issue:** September 2026
**Analysis Period:** September 2026
**Source:** [SentryDigest](https://ricomanifesto.github.io/SentryDigest/feed.xml)
**Source Issue:** [SentryDigest 2026-09-28](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/)
**Articles Analyzed:** 30
**GRC-Relevant Articles:** 30
**Authoring Model:** nvidia/nemotron-3-ultra-550b-a55b:free
**Requested Route:** openrouter/nvidia/nemotron-3-ultra-550b-a55b:free
**Analysis Mode:** Model-backed

## Executive Summary

Active exploitation of critical infrastructure vulnerabilities has accelerated across multiple vendor platforms this quarter. CISA added two Citrix NetScaler remote code execution flaws (CVE-2026-88771, CVE-2026-88772) and a Microsoft SharePoint code injection vulnerability (CVE-2026-65660) to its Known Exploited Vulnerabilities catalog, confirming active attacks in the wild [CISA Says Attackers Are Exploiting Two Critical Citrix NetScaler Flaws Globally](https://thehackernews.com/2026/09/cisa-says-attackers-are-exploiting-two.html) [Citrix confirms two NetScaler RCE zero-days exploited in attacks](https://www.bleepingcomputer.com/news/security/citrix-admins-warned-to-shut-down-netscalers-over-2-exploited-zero-days/) [SharePoint RCE and MikroTik RouterOS Flaws Actively Exploited in the Wild](https://thehackernews.com/2026/09/sharepoint-rce-and-mikrotik-routeros.html).

Threat actors are demonstrating increased sophistication in bypassing defensive controls and weaponizing AI capabilities. The ShinyHunters extortion group employed a URL-encoding technique to circumvent web application firewall protections for Oracle PeopleSoft CVE-2026-35273, while the JadePuffer ransomware operator leveraged agentic AI to conduct reconnaissance, credential theft, and destructive actions against Azure tenants [ShinyHunters uses WAF bypass trick in Oracle PeopleSoft attacks](https://www.bleepingcomputer.com/news/security/shinyhunters-uses-waf-bypass-trick-in-oracle-peoplesoft-attacks/) [JadePuffer agentic AI attacks target Azure, destroy cloud resources](https://www.bleepingcomputer.com/news/security/jadepuffer-agentic-ai-attacks-target-azure-destroy-cloud-resources/) [JadePuffer AI Actor Compromises Azure Tenant in Destructive Cloud Attack](https://www.darkreading.com/cloud-security/jadepuffer-ai-actor-azure-tenant-destructive-cloud-attack).

Identity compromise at scale is enabling downstream attacks across the software supply chain. Infostealer malware exposed AI platform credentials and sessions tied to more than 80,000 corporate domains, creating risks ranging from conversation theft to large language model hijacking, while a malicious Chrome Web Store extension masquerading as an ad blocker was downloaded by millions of users before detection [80,000+ Organizations Had AI Logins Stolen: From Shadow AI to LLMjacking](https://www.bleepingcomputer.com/news/security/80-000-plus-organizations-had-ai-logins-stolen-from-shadow-ai-to-llmjacking/) [Chrome Store Hosts 'Poper Blocker' Spyware Downloaded by Millions](https://www.darkreading.com/application-security/chrome-store-poper-blocker-spyware-downloaded-millions).

Governance gaps for autonomous AI agents are widening as deployment outpaces control frameworks. Only 47% of CISOs report confidence in identifying every AI agent in their environment, and new botnet malware (Carbonato) is compromising exposed Docker daemons to deploy Telegram-controlled AI agent frameworks without authorization [Webinar: How to Govern AI Agents, Reduce Excessive Access, and Control Shadow AI](https://thehackernews.com/2026/09/webinar-how-to-govern-ai-agents-reduce.html) [Carbonato Botnet Compromises Docker Hosts to Deploy Telegram-Controlled Hermes AI Agent](https://thehackernews.com/2026/09/carbonato-botnet-compromises-docker.html).

## Key Regulatory Developments

| Regulation / Framework | Development | Business Impact | Source |
|------------------------|-------------|-----------------|--------|
| CISA Known Exploited Vulnerabilities (KEV) Catalog | Added CVE-2026-88771, CVE-2026-88772 (Citrix NetScaler) and CVE-2026-65660 (Microsoft SharePoint) citing active exploitation | Mandates emergency patching for federal agencies; drives private-sector prioritization under binding operational directives and cyber insurance requirements | [CISA Says Attackers Are Exploiting Two Critical Citrix NetScaler Flaws Globally](https://thehackernews.com/2026/09/cisa-says-attackers-are-exploiting-two.html) [SharePoint RCE and MikroTik RouterOS Flaws Actively Exploited in the Wild](https://thehackernews.com/2026/09/sharepoint-rce-and-mikrotik-routeros.html) **Evidence:** [Citrix confirms two NetScaler RCE zero-days exploited in attacks](https://www.bleepingcomputer.com/news/security/citrix-admins-warned-to-shut-down-netscalers-over-2-exploited-zero-days/) |

## Industry Impact Analysis

| Sector | Primary Exposure | Observed Threat Activity |
|--------|------------------|--------------------------|
| Technology / Cloud Services | Azure tenant compromise via agentic AI; Docker daemon exposure | JadePuffer destructive attacks; Carbonato botnet deploying Hermes AI agent [JadePuffer agentic AI attacks target Azure, destroy cloud resources](https://www.bleepingcomputer.com/news/security/jadepuffer-agentic-ai-attacks-target-azure-destroy-cloud-resources/) [Carbonato Botnet Compromises Docker Hosts to Deploy Telegram-Controlled Hermes AI Agent](https://thehackernews.com/2026/09/carbonato-botnet-compromises-docker.html) |
| Enterprise Software (ERP/CRM) | Oracle PeopleSoft CVE-2026-35273; Citrix NetScaler ADC/Gateway | ShinyHunters WAF bypass exploitation; active RCE exploitation of NetScaler [ShinyHunters uses WAF bypass trick in Oracle PeopleSoft attacks](https://www.bleepingcomputer.com/news/security/shinyhunters-uses-waf-bypass-trick-in-oracle-peoplesoft-attacks/) [Citrix confirms two NetScaler RCE zero-days exploited in attacks](https://www.bleepingcomputer.com/news/security/citrix-admins-warned-to-shut-down-netscalers-over-2-exploited-zero-days/) |
| Collaboration Platforms | Microsoft SharePoint CVE-2026-65660 | Active code injection exploitation [SharePoint RCE and MikroTik RouterOS Flaws Actively Exploited in the Wild](https://thehackernews.com/2026/09/sharepoint-rce-and-mikrotik-routeros.html) |
| Consumer / End-User | Chrome Web Store extension vetting | 'Poper Blocker' spyware downloaded by millions [Chrome Store Hosts 'Poper Blocker' Spyware Downloaded by Millions](https://www.darkreading.com/application-security/chrome-store-poper-blocker-spyware-downloaded-millions) |
| Cross-Sector | AI credential theft (80,000+ corporate domains) | Infostealer-driven LLMjacking risk [80,000+ Organizations Had AI Logins Stolen: From Shadow AI to LLMjacking](https://www.bleepingcomputer.com/news/security/80-000-plus-organizations-had-ai-logins-stolen-from-shadow-ai-to-llmjacking/) |

## Risk Assessment

| Risk Category | Likelihood | Impact | Key Indicators |
|---------------|------------|--------|----------------|
| Critical Infrastructure Exploitation | High | Critical | Three KEV additions in single week; CVSS 9.5 and 8.8 scores; unauthenticated RCE vectors [CISA Says Attackers Are Exploiting Two Critical Citrix NetScaler Flaws Globally](https://thehackernews.com/2026/09/cisa-says-attackers-are-exploiting-two.html) [SharePoint RCE and MikroTik RouterOS Flaws Actively Exploited in the Wild](https://thehackernews.com/2026/09/sharepoint-rce-and-mikrotik-routeros.html) |
| Defensive Control Bypass | High | High | WAF evasion via URL encoding; attacker adaptation after law enforcement action [ShinyHunters uses WAF bypass trick in Oracle PeopleSoft attacks](https://www.bleepingcomputer.com/news/security/shinyhunters-uses-waf-bypass-trick-in-oracle-peoplesoft-attacks/) [Dutch Police Arrest ‘Reformed’ Hacker in Shiny Hunters Investigation](https://krebsonsecurity.com/2026/09/dutch-police-arrest-reformed-hacker-in-shiny-hunters-investigation/) |
| Agentic AI Weaponization | Medium | Critical | Autonomous reconnaissance, credential theft, resource destruction in cloud environments [JadePuffer agentic AI attacks target Azure, destroy cloud resources](https://www.bleepingcomputer.com/news/security/jadepuffer-agentic-ai-attacks-target-azure-destroy-cloud-resources/) [JadePuffer AI Actor Compromises Azure Tenant in Destructive Cloud Attack](https://www.darkreading.com/cloud-security/jadepuffer-ai-actor-azure-tenant-destructive-cloud-attack) |
| AI Identity Compromise at Scale | High | High | 80,000+ corporate domains exposed; active marketplace for stolen AI sessions [80,000+ Organizations Had AI Logins Stolen: From Shadow AI to LLMjacking](https://www.bleepingcomputer.com/news/security/80-000-plus-organizations-had-ai-logins-stolen-from-shadow-ai-to-llmjacking/) |
| Unauthorized AI Agent Deployment | Medium | High | Botnet installing AI frameworks on compromised Docker hosts; governance coverage at 47% [Carbonato Botnet Compromises Docker Hosts to Deploy Telegram-Controlled Hermes AI Agent](https://thehackernews.com/2026/09/carbonato-botnet-compromises-docker.html) [Webinar: How to Govern AI Agents, Reduce Excessive Access, and Control Shadow AI](https://thehackernews.com/2026/09/webinar-how-to-govern-ai-agents-reduce.html) |
| Supply Chain / Extension Trust | Medium | High | Malicious extension with Google store approval; millions of downloads [Chrome Store Hosts 'Poper Blocker' Spyware Downloaded by Millions](https://www.darkreading.com/application-security/chrome-store-poper-blocker-spyware-downloaded-millions) |

## Recommendations for Action

1. **Enforce Emergency Patching for KEV-Listed Vulnerabilities**
   Prioritize immediate deployment of Citrix NetScaler ADC/Gateway fixes for CVE-2026-88771 and CVE-2026-88772, and Microsoft SharePoint updates for CVE-2026-65660. Validate patch application through vulnerability scanning and configuration audit [CISA Says Attackers Are Exploiting Two Critical Citrix NetScaler Flaws Globally](https://thehackernews.com/2026/09/cisa-says-attackers-are-exploiting-two.html) [Citrix confirms two NetScaler RCE zero-days exploited in attacks](https://www.bleepingcomputer.com/news/security/citrix-admins-warned-to-shut-down-netscalers-over-2-exploited-zero-days/) [SharePoint RCE and MikroTik RouterOS Flaws Actively Exploited in the Wild](https://thehackernews.com/2026/09/sharepoint-rce-and-mikrotik-routeros.html).

2. **Harden WAF and Application Layer Defenses**
   Review and update web application firewall rule sets to detect URL-encoding evasion techniques. Implement behavioral anomaly detection for Oracle PeopleSoft and similar ERP endpoints [ShinyHunters uses WAF bypass trick in Oracle PeopleSoft attacks](https://www.bleepingcomputer.com/news/security/shinyhunters-uses-waf-bypass-trick-in-oracle-peoplesoft-attacks/).

3. **Establish AI Agent Governance Program**
   Deploy discovery tooling to inventory all autonomous agents (AI agents, service accounts, bot frameworks) across cloud tenants and container runtimes. Enforce least-privilege policies, require human approval for destructive actions, and monitor for unauthorized framework deployments such as Hermes Agent [Webinar: How to Govern AI Agents, Reduce Excessive Access, and Control Shadow AI](https://thehackernews.com/2026/09/webinar-how-to-govern-ai-agents-reduce.html) [Carbonato Botnet Compromises Docker Hosts to Deploy Telegram-Controlled Hermes AI Agent](https://thehackernews.com/2026/09/carbonato-botnet-compromises-docker.html).

4. **Rotate and Monitor AI Platform Credentials**
   Conduct immediate credential rotation for all corporate AI platform accounts. Implement session monitoring, anomaly detection for unusual model invocation patterns, and integrate infostealer intelligence feeds to identify exposed sessions [80,000+ Organizations Had AI Logins Stolen: From Shadow AI to LLMjacking](https://www.bleepingcomputer.com/news/security/80-000-plus-organizations-had-ai-logins-stolen-from-shadow-ai-to-llmjacking/).

5. **Strengthen Extension and Container Supply Chain Controls**
   Restrict browser extension installation to approved catalog entries with verified publishers. Scan Docker daemon exposure externally; enforce authentication and TLS on all container runtime APIs [Chrome Store Hosts 'Poper Blocker' Spyware Downloaded by Millions](https://www.darkreading.com/application-security/chrome-store-poper-blocker-spyware-downloaded-millions) [Carbonato Botnet Compromises Docker Hosts to Deploy Telegram-Controlled Hermes AI Agent](https://thehackernews.com/2026/09/carbonato-botnet-compromises-docker.html).

6. **Prepare for Threat Actor Escalation Post-Enforcement**
   Heighten monitoring for retaliatory activity following law enforcement actions against ransomware and extortion groups. Correlate threat intelligence on ShinyHunters and Cl0p activity with internal alerting [Dutch Police Arrest ‘Reformed’ Hacker in Shiny Hunters Investigation](https://krebsonsecurity.com/2026/09/dutch-police-arrest-reformed-hacker-in-shiny-hunters-investigation/).

## Source Highlights

- [CISA Says Attackers Are Exploiting Two Critical Citrix NetScaler Flaws Globally](https://thehackernews.com/2026/09/cisa-says-attackers-are-exploiting-two.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-d10d67a734db)
- [Citrix confirms two NetScaler RCE zero-days exploited in attacks](https://www.bleepingcomputer.com/news/security/citrix-admins-warned-to-shut-down-netscalers-over-2-exploited-zero-days/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-0954e8dba9d8)
- [ShinyHunters uses WAF bypass trick in Oracle PeopleSoft attacks](https://www.bleepingcomputer.com/news/security/shinyhunters-uses-waf-bypass-trick-in-oracle-peoplesoft-attacks/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-77ddfbcd4e34)
- [SharePoint RCE and MikroTik RouterOS Flaws Actively Exploited in the Wild](https://thehackernews.com/2026/09/sharepoint-rce-and-mikrotik-routeros.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-049c4c6d156c)
- [Chrome Store Hosts 'Poper Blocker' Spyware Downloaded by Millions](https://www.darkreading.com/application-security/chrome-store-poper-blocker-spyware-downloaded-millions) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-9ea947543a47)
- [JadePuffer agentic AI attacks target Azure, destroy cloud resources](https://www.bleepingcomputer.com/news/security/jadepuffer-agentic-ai-attacks-target-azure-destroy-cloud-resources/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-178f19609d47)
- [JadePuffer AI Actor Compromises Azure Tenant in Destructive Cloud Attack](https://www.darkreading.com/cloud-security/jadepuffer-ai-actor-azure-tenant-destructive-cloud-attack) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-1820f6c11fcc)
- [Dutch Police Arrest ‘Reformed’ Hacker in Shiny Hunters Investigation](https://krebsonsecurity.com/2026/09/dutch-police-arrest-reformed-hacker-in-shiny-hunters-investigation/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-c919c2b059f3)
- [80,000+ Organizations Had AI Logins Stolen: From Shadow AI to LLMjacking](https://www.bleepingcomputer.com/news/security/80-000-plus-organizations-had-ai-logins-stolen-from-shadow-ai-to-llmjacking/) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-cdfc9fd9c096)
- [Webinar: How to Govern AI Agents, Reduce Excessive Access, and Control Shadow AI](https://thehackernews.com/2026/09/webinar-how-to-govern-ai-agents-reduce.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-e51480e96d84)
- [Carbonato Botnet Compromises Docker Hosts to Deploy Telegram-Controlled Hermes AI Agent](https://thehackernews.com/2026/09/carbonato-botnet-compromises-docker.html) · [View in SentryDigest](https://ricomanifesto.github.io/SentryDigest/archive/2026-09-28/#reporting-a2739f1e6c8a)
