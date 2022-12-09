#ifndef OMFLINKEDDATA_H
#define OMFLINKEDDATA_H
/*
 * Fledge OSIsoft OMF interface to PI Server.
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <map>
#include <reading.h>
#include <OMFHint.h>

/**
 * The OMFLinkedData class.
 * A reading is formatted with OMF specifications using the linked
 * type creation scheme supported for OMF Version 1.2 onwards.
 *
 * This is based on the new mechanism discussed at AvevaWorld 2022 and
 * the mechanism is detail in the Google Doc,
 * https://docs.google.com/document/d/1w0e7VRqX7xzc0lEBLq-sYhgaHE0ABasOa6EC9dJMrMs/edit
 *
 * The principle is to use links to contianers in OMF with each contianer beign a single
 * data point in the asset. There are no specific types for the assets, they share a set
 * of base tyoes vis these links. This should allow for readings that have different sets
 * of datapoints for each asset.
 *
 * It is also a goal of this mechanism to move away from the need to persist state data
 * between invocations and make the process more robust.
 */
class OMFLinkedData
{
	public:
		OMFLinkedData(  std::map<std::string, std::string> *containerSent,
				std::map<std::string, bool> *assetSent,
				std::map<std::string, bool> *linkSent,
				const OMF_ENDPOINT PIServerEndpoint = ENDPOINT_CR) :
					m_containerSent(containerSent),
					m_assetSent(assetSent),
					m_linkSent(linkSent),
					m_endpoint(PIServerEndpoint) {};
		std::string 	processReading(const Reading& reading,
				const std::string& DefaultAFLocation = std::string(),
				OMFHints *hints = NULL);
		bool		flushContainers(HttpSender& sender, const std::string& path, std::vector<std::pair<std::string, std::string> >& header);
	private:
		std::string	sendContainer(std::string& link, Datapoint *dp);
		bool		isTypeSupported(DatapointValue& dataPoint)
				{
					switch (dataPoint.getType())
					{
						case DatapointValue::DatapointTag::T_FLOAT:
						case DatapointValue::DatapointTag::T_INTEGER:
						case DatapointValue::DatapointTag::T_STRING:
							return true;
						default:
							return false;
					}
				};

	private:
		/**
		 * The container for this asset and data point has been sent in
		 * this session.
		 */
		std::map<std::string, std::string>	*m_containerSent;

		/**
		 * The data message for this asset and data point has been sent in
		 * this session.
		 */
		std::map<std::string, bool>		*m_assetSent;

		/**
		 * The link for this asset and data point has been sent in
		 * this session.
		 */
		std::map<std::string, bool>		*m_linkSent;

		/**
		 * The endpoint to which we are sending data
		 */
		OMF_ENDPOINT				m_endpoint;


		/**
		 * The set of containers to flush
		 */
		std::string				m_containers;
};
#endif
