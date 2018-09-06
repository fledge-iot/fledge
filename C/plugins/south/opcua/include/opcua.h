#ifndef _OPCUA_H
#define _OPCUA_H
/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <string>
#include <opc/ua/client/client.h>
#include <opc/ua/node.h>
#include <opc/ua/subscription.h>
#include <reading.h>
#include <logger.h>

class OpcUaClient;

class OPCUA
{
	public:
		OPCUA(const std::string& url);
		~OPCUA();
		void		addSubscription(const std::string& parent);
		void		setAssetName(const std::string& name);
		void		start();
		void		stop();
		void		ingest(std::vector<Datapoint *>  points);
		void		registerIngest(void *data, void (*cb)(void *, Reading))
				{
					m_ingest = cb;
					m_data = data;
				}

	private:
		std::vector<std::string>	m_subscriptions;
		std::string			m_url;
		std::string			m_asset;
		OpcUa::UaClient			*m_client;
		void				(*m_ingest)(void *, Reading);
		void				*m_data;
		OpcUaClient			*m_subClient;
};

class OpcUaClient : public OpcUa::SubscriptionHandler
{ 
	public:
	  	OpcUaClient(OPCUA *opcua) : m_opcua(opcua) {};
		void DataChange(uint32_t handle, const OpcUa::Node & node, const OpcUa::Variant & val, OpcUa::AttributeId attr) override
		{ 
			std::vector<Datapoint *>	points;
			DatapointValue value(val.ToString());
			points.push_back(new Datapoint(node.GetId().GetStringIdentifier(), value));
			m_opcua->ingest(points);
		};
	private:
		OPCUA		*m_opcua;
};
#endif
