---
doc_id: it_security_policy
title: IT Security Policy
visible_to: [it]
---
# IT Security Policy

This policy defines security operations procedures for the IT Security
team. It supplements the company-wide Acceptable Use Policy.

## Incident Response

Security incidents are classified into 4 severity tiers. Tier 1 (active
data exfiltration or ransomware) requires the on-call security engineer to
begin containment within 15 minutes of detection and notify the CISO
immediately. Tier 2–4 incidents follow a 1-hour, 4-hour, and next-business-day
response SLA respectively.

## Access Reviews

Privileged access (admin rights on production systems, access to the
customer database) is reviewed quarterly. Any account with privileged
access not used in 90 days is automatically flagged for revocation pending
manager confirmation.

## Vulnerability Management

Critical vulnerabilities (CVSS 9.0+) affecting internet-facing systems must
be patched within 72 hours of disclosure. High-severity vulnerabilities
(CVSS 7.0–8.9) have a 14-day patch SLA. Exceptions require a documented
risk acceptance signed by the CISO.

## Third-Party Access

Vendors and contractors requiring system access must go through the
third-party risk assessment before provisioning, and their access is
automatically revoked 30 days after contract end unless explicitly
extended.

## Logging and Monitoring

Production systems must ship logs to the central SIEM with a minimum 1-year
retention. Any attempt to disable or tamper with logging on a production
system is itself treated as a Tier 1 security event.

## Breach Notification

Confirmed breaches involving customer data trigger the joint IT
Security/Legal breach response process; do not communicate externally
about a suspected breach without Legal's involvement, given regulatory
notification deadlines.
