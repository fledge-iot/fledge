# Security Policy

## Reporting a Vulnerability

The Fledge project takes security vulnerabilities seriously.

Please do not report security vulnerabilities through public GitHub issues, discussions, or other public channels.

Security vulnerabilities should be reported privately to:

[**support@helindata.com**](mailto:support@helindata.com)

Please include as much information as possible to help us investigate the issue, including:

- A description of the vulnerability
- The affected Fledge component or plugin
- The affected version or versions
- Steps to reproduce the issue
- Potential impact
- Any known exploitation or evidence of exploitation
- Suggested remediation, if available

Please avoid sharing sensitive vulnerability information publicly until the issue has been investigated and, where appropriate, a coordinated disclosure has taken place.

## Security Response Process

After receiving a vulnerability report, the project maintainers will:

1. Acknowledge and review the report.
2. Determine whether the issue affects Fledge or related project components.
3. Assess the severity and potential impact.
4. Coordinate remediation with the relevant maintainers.
5. Coordinate disclosure and release information where appropriate.
6. Coordinate with the project's Linux Foundation CRA steward when required.

Where necessary, reporters may be contacted for additional information during the investigation.

## Actively Exploited Vulnerabilities and Severe Security Incidents

If you believe a vulnerability is being actively exploited, or you are reporting a severe security incident affecting the project, please clearly indicate this in your report and contact:

[**support@helindata.com**](mailto:support@helindata.com)

Examples of severe security incidents may include:

- Known active exploitation of a vulnerability affecting Fledge
- Compromise of Fledge release artifacts
- Compromise of the project's build or release infrastructure
- Compromise of signing keys, release credentials, or other security-sensitive credentials
- Publication or distribution of malicious or unauthorized project artifacts

Such reports will be treated as urgent and escalated to the appropriate project maintainers and, where applicable, the project's CRA steward.

## Coordinated Disclosure

The Fledge project supports coordinated vulnerability disclosure.

We ask security researchers and users to allow reasonable time for the issue to be investigated and remediated before publishing vulnerability details.

Where appropriate, the project may coordinate:

- Security fixes
- New software releases
- Security advisories
- CVE assignment
- Communication with downstream users or distributors
- Communication with the Linux Foundation and other relevant parties

## Supported Versions

Security fixes are generally provided for versions of Fledge that are actively maintained by the project.

Users are encouraged to run the latest supported release whenever possible.

Older releases may no longer receive security updates. Where a vulnerability affects an unsupported version, users may be required to upgrade to a supported release.

## Cyber Resilience Act (CRA) Stewardship

This project is supported under the Linux Foundation CRA stewardship framework, as described at https://www.linuxfoundation.org/security.

Security vulnerabilities should be reported through the mechanisms described above, which we will coordinate with our CRA steward.

For actively exploited vulnerabilities and severe incidents that may require CRA escalation, please use the project's emergency security reporting mechanism by contacting [**support@helindata.com**](mailto:support@helindata.com) immediately.

## Scope

This security policy applies to the Fledge project and project-maintained components.

Vulnerabilities affecting third-party dependencies should also be reported to the relevant upstream project where appropriate. If a third-party vulnerability creates a security impact specifically within Fledge, it may also be reported through the process described above.
