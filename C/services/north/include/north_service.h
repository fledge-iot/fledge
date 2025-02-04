#ifndef _NORTH_SERVICE_H
#define _NORTH_SERVICE_H
/*
 * Fledge north service.
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <logger.h>
#include <north_plugin.h>
#include <service_handler.h>
#include <storage_client.h>
#include <config_category.h>
#include <filter_plugin.h>
#include <mutex>
#include <condition_variable>
#include <audit_logger.h>
#include <perfmonitors.h>
#include <data_load.h>
#include <data_sender.h>

#define SERVICE_NAME  "Fledge North"

/**
 * State bits for the south pipeline debugger
 */
#define DEBUG_ATTACHED		0x01
#define DEBUG_SUSPENDED		0x02
#define DEBUG_ISOLATED		0x04

/**
 * The NorthService class. This class is the core
 * of the service that provides north side services
 * to Fledge.
 */
class NorthService : public ServiceAuthHandler {
	public:
		NorthService(const std::string& name,
				const std::string& token = "");
		virtual ~NorthService();
		void 				start(std::string& coreAddress,
						      unsigned short corePort);
		void 				stop();
		void				shutdown();
		void				restart();
		void				configChange(const std::string&, const std::string&);
		void				configChildCreate(const std::string& , const std::string&, const std::string&){};
		void				configChildDelete(const std::string& , const std::string&){};
		bool				isRunning() { return !m_shutdown; };
		const std::string&		getName() { return m_name; };
		const std::string&		getPluginName() { return m_pluginName; };
		void				pause();
		void				release();
		bool				write(const std::string& name, const std::string& value, const ControlDestination);
		bool				write(const std::string& name, const std::string& value, const ControlDestination, const std::string& arg);
		int				operation(const std::string& name, int paramCount, char *names[], char *parameters[], const ControlDestination);
		int				operation(const std::string& name, int paramCount, char *names[], char *parameters[], const ControlDestination, const std::string& arg);
		void				setDryRun() { m_dryRun = true; };
		bool				getDryRun() { return m_dryRun; };
		void				alertFailures();
		void				clearFailures();
		// Debugger Entry point
		bool				attachDebugger()
						{
							if (m_dataLoad)
							{
								m_debugState = DEBUG_ATTACHED;
								return m_dataLoad->attachDebugger();
							}
							return false;
						};
		void				detachDebugger()
						{
							if (m_dataLoad)
								m_dataLoad->detachDebugger();
							suspendDebugger(false);
							isolateDebugger(false);
							m_debugState = 0;
						};
		void				setDebuggerBuffer(unsigned int size)
						{
							if (m_dataLoad)
								m_dataLoad->setDebuggerBuffer(size);
						};
		std::string			getDebuggerBuffer()
						{
							if (m_dataLoad)
								return m_dataLoad->getDebuggerBuffer();
							return "";
						};
		void				suspendDebugger(bool suspend)
						{
							if (m_dataLoad)
							{
								m_dataLoad->suspendIngest(suspend);
								if (suspend)
									m_debugState |= DEBUG_SUSPENDED;
								else
									m_debugState &= ~(unsigned int)DEBUG_SUSPENDED;
							}
						};
		void				isolateDebugger(bool isolate)
						{
							if (m_dataLoad)
							{
								m_dataLoad->isolate(isolate);
								if (isolate)
									m_debugState |= DEBUG_ISOLATED;
								else
									m_debugState &= ~(unsigned int)DEBUG_ISOLATED;
							}
						};
		void				stepDebugger(unsigned int steps)
						{
							if (m_dataLoad)
								m_dataLoad->stepDebugger(steps);
						}
		void				replayDebugger()
						{
							if (m_dataLoad)
								m_dataLoad->replayDebugger();
						};
		std::string			debugState();
		bool				debuggerAttached()
						{
							return m_debugState & DEBUG_ATTACHED;
						}
		
	private:
		void				addConfigDefaults(DefaultConfigCategory& defaults);
		bool 				loadPlugin();
		void 				createConfigCategories(DefaultConfigCategory configCategory, std::string parent_name,std::string current_name);
		void				restartPlugin();
	private:
		std::string			controlSource();
		bool				sendToService(const std::string& southService, const std::string& name, const std::string& value);
		bool				sendToDispatcher(const std::string& path, const std::string& payload);
		DataLoad			*m_dataLoad;
		DataSender			*m_dataSender;
		NorthPlugin			*northPlugin;
		std::string			m_pluginName;
		Logger        			*logger;
		AssetTracker			*m_assetTracker;
		volatile bool			m_shutdown;
		ConfigCategory			m_config;
		ConfigCategory			m_configAdvanced;
		StorageClient			*m_storage;
		std::mutex			m_mutex;
                std::condition_variable		m_cv;
		PluginData			*m_pluginData;
		bool				m_restartPlugin;
		const std::string		m_token;
		bool				m_allowControl;
		bool				m_dryRun;
		bool				m_requestRestart;
		AuditLogger			*m_auditLogger;
		PerformanceMonitor		*m_perfMonitor;
		unsigned int			m_debugState;
};
#endif
