#ifndef _AUDIT_LOGGER_H
#define _AUDIT_LOGGER_H
/*
 * Fledge Singleton Audit Logger interface
 *
 * Copyright (c) 2023 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <management_client.h>
#include <string>

/**
 * A singleton class for access to the audit logger within services. The
 * service must create this with the maagement client before any access to it is used.
 */
class AuditLogger {
	public:
		AuditLogger(ManagementClient *mgmt);
		~AuditLogger();

		static AuditLogger	*getLogger();
		static void		auditLog(const std::string& code,
						const std::string& level,
						const std::string& data = "");

		void			audit(const std::string& code,
						const std::string& level,
						const std::string& data = "");

	private:
		static AuditLogger	*m_instance;
		ManagementClient	*m_mgmt;
};
#endif
