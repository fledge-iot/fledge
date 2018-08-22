/*
 * FogLAMP south service plugin
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <opcua.h>
#include <reading.h>
#include <logger.h>

using namespace std;

class SubClient : public OpcUa::SubscriptionHandler
{ 
	public:
	  	SubClient(OPCUA *opcua) : m_opcua(opcua) {};
		void DataChange(uint32_t handle, const OpcUa::Node & node, const OpcUa::Variant & val, OpcUa::AttributeId attr) override
		{ 
			vector<Datapoint *>	points;
			DatapointValue value(val.ToString());
			points.push_back(new Datapoint(node.GetId().GetStringIdentifier(), value));
			m_opcua->ingest(points);
		};
	private:
		OPCUA		*m_opcua;
};

/**
 * Constructor for the opcua plugin
 */
OPCUA::OPCUA(const string& url) : m_url(url)
{
}

/**
 * Destructor for the opcua interface
 */
OPCUA::~OPCUA()
{
}

/**
 * Set the asset name for the asset we write
 *
 * @param asset Set the name of the asset with insert into readings
 */
void
OPCUA::setAssetName(const std::string& asset)
{
	m_asset = asset;
}

/**
 * Add a subscription parent node to the list
 */
void
OPCUA::addSubscription(const string& parent, const string& child)
{
	m_subscriptions.push_back(pair<string, string>({parent, child}));

}

void
OPCUA::start()
{
	m_client = new OpcUa::UaClient(Logger::getLogger());
	m_client->Connect(m_url);

	OpcUa::Node root = m_client->GetRootNode();

	SubClient sclt(this);
	OpcUa::Subscription::SharedPtr sub = m_client->CreateSubscription(100, sclt);
	for (pair<string, string> item : m_subscriptions)
	{
		vector<string> varPath({"Objects", item.first, item.second});
		OpcUa::Node myvar = root.GetChild(varPath);
		sub->SubscribeDataChange(myvar);
	}
}

/**
 * Take a reading from the opcua
 */
void OPCUA::ingest(vector<Datapoint *>	points)
{
	(*m_ingest)(m_data, Reading(m_asset, points));
}
