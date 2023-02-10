/*
 * Fledge Singleton Audit Logger interface
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <audit_logger.h>

AuditLogger *AuditLogger::m_instance = 0;

using namespace std;

/**
 * Constructor for an audit logger that is passed
 * the management client. This must be called early in
 * a service or task creation before any audit logs are
 * created.
 *
 * @param mgmt	Pointer to the management client
 */
AuditLogger::AuditLogger(ManagementClient *mgmt) : m_mgmt(mgmt)
{
	m_instance = this;
}

/**
 * Destructor for an audit logger
 */
AuditLogger::~AuditLogger()
{
}

/**
 * Get the audit logger singleton
 */
AuditLogger *AuditLogger::getLogger()
{
	if (!m_instance)
	{
		Logger::getLogger()->error("An attempt has been made to obtain the audit logger before it has been created.");
	}
	return m_instance;
}

void AuditLogger::auditLog(const string& code,
			const string& level,
			const string& data)
{
	if (m_instance)
	{
		m_instance->audit(code, level, data);
	}
	else
	{
		Logger::getLogger()->error("An attempt has been made to log an audit event when no audit logger is available");
		Logger::getLogger()->error("Audit event is: %s, %s, %s", code.c_str(), level.c_str(), data.c_str());
	}
}

/**
 * Log an audit message
 *
 * @param code	The audit code
 * @param level	The audit level
 * @param data	Optional data associated with the audit entry
 */
void AuditLogger::audit(const string& code,
			const string& level,
			const string& data)
{
	m_mgmt->addAuditEntry(code, level, data);
}
