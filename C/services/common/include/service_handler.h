#ifndef _SERVICE_HANDLER_H
#define _SERVICE_HANDLER_H
/*
 * Fledge service class
 *
 * Copyright (c) 2017 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <config_category.h>
#include <string>
#include <management_client.h>

/**
 * ServiceHandler abstract class - the interface that services using the
 * management API must provide.
 */
class ServiceHandler
{
	public:
		virtual void	shutdown() = 0;
		virtual void	restart() = 0;
		virtual void	configChange(const std::string& category, const std::string& config) = 0;
		virtual void	configChildCreate(const std::string& parent_category, const std::string& category, const std::string& config) = 0;
		virtual void	configChildDelete(const std::string& parent_category, const std::string& category) = 0;
		virtual bool	isRunning() = 0;
		virtual bool	securityChange(const std::string &payload) { return payload.empty(); };
};

/**
 * ServiceAuthHandler adds security to the base class ServiceHandler
 */
class ServiceAuthHandler : public ServiceHandler
{
	public:
		ServiceAuthHandler() : m_refreshThread(NULL), m_refreshRunning(true) {};
		virtual ~ServiceAuthHandler() { if (m_refreshThread) { m_refreshRunning = false; m_refreshThread->join(); delete m_refreshThread; } };
		std::string&	getName() { return m_name; };
		std::string&	getType() { return m_type; };
		bool		createSecurityCategories(ManagementClient* mgtClient, bool dryRun);
		bool		updateSecurityCategory(const std::string& newCategory);
		void		setInitialAuthenticatedCaller();
		void		setAuthenticatedCaller(bool enabled);
		bool		getAuthenticatedCaller();
		// ACL verification (for Dispatcher)
		bool		AuthenticationMiddlewareACL(std::shared_ptr<HttpServer::Response> response,
							std::shared_ptr<HttpServer::Request> request,
							const std::string& serviceName,
							const std::string& serviceType);
		// Hanlder for Dispatcher
		bool		AuthenticationMiddlewareCommon(std::shared_ptr<HttpServer::Response> response,
							std::shared_ptr<HttpServer::Request> request,
							std::string& callerName,
							std::string& callerType);
		// Handler for South services: token verifation and service ACL check
		void		AuthenticationMiddlewarePUT(std::shared_ptr<HttpServer::Response> response,
							std::shared_ptr<HttpServer::Request> request,
							std::function<void(
								std::shared_ptr<HttpServer::Response>,
								std::shared_ptr<HttpServer::Request>)> funcPUT);
		void		refreshBearerToken();
 		// Send a good HTTP response to the caller
		void		respond(std::shared_ptr<HttpServer::Response> response,
							const std::string& payload)
				{
					*response << "HTTP/1.1 200 OK\r\n"
						<< "Content-Length: " << payload.length() << "\r\n"
						<<  "Content-type: application/json\r\n\r\n"
						<< payload;
				};
 		// Send an error messagei HTTP response to the caller with given HTTP code
		void		respond(std::shared_ptr<HttpServer::Response> response,
							SimpleWeb::StatusCode code,
							const std::string& payload)
				{
					*response << "HTTP/1.1 " << status_code(code) << "\r\n"
						<< "Content-Length: " << payload.length() << "\r\n"
						<<  "Content-type: application/json\r\n\r\n"
						<< payload;
				};
		static ManagementClient *
				getMgmtClient() { return m_mgtClient; };
		bool		securityChange(const std::string &payload);

	private:
		bool		verifyURL(const std::string& path,
					const std::string& sName,
					const std::string& sType);
		bool		verifyService(const std::string& sName,
					const std::string &sType);

	protected:
		std::string	m_name;
		std::string	m_type;
		// Management client pointer
		static ManagementClient
				*m_mgtClient;

	private:
		// Security configuration change mutex
		std::mutex	m_mtx_config;
		// Authentication is enabled for API endpoints
		bool		m_authentication_enabled;
		// Security configuration
		ConfigCategory	m_security;
		// Service ACL
		ACL		m_service_acl;
		std::thread	*m_refreshThread;
		bool		m_refreshRunning;
};

#endif
