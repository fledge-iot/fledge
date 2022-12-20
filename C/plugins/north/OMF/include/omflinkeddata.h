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
#include <vector>

/**
 * The OMFLinkedData class.
 * A reading is formatted with OMF specifications using the linked
 * type creation scheme supported for OMF Version 1.2 onwards.
 *
 * This is based on the new mechanism discussed at AVEVA World 2022 and
 * the mechanism is detailed in the Google Doc,
 * https://docs.google.com/document/d/1w0e7VRqX7xzc0lEBLq-sYhgaHE0ABasOa6EC9dJMrMs/edit
 *
 * The principle is to use links to containers in OMF with each container being a single
 * data point in the asset. There are no specific types for the assets, they share a set
 * of base types via these links. This should allow for readings that have different sets
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
					m_endpoint(PIServerEndpoint),
       					m_doubleFormat("float64"),
					m_integerFormat("int64")
					{};
		std::string 	processReading(const Reading& reading,
				const std::string& DefaultAFLocation = std::string(),
				OMFHints *hints = NULL);
		bool		flushContainers(HttpSender& sender, const std::string& path, std::vector<std::pair<std::string, std::string> >& header, bool noRecovery);
		void		setFormats(const std::string& doubleFormat, const std::string& integerFormat)
				{
					m_doubleFormat = doubleFormat;
					m_integerFormat = integerFormat;
				};
	private:
		std::string	sendContainer(std::string& link, Datapoint *dp, const std::string& format,  OMFHints * hints);
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
		bool		recoverContainerError(HttpSender& sender, const std::string& path, std::string& response);
		bool		recoverContainer(HttpSender& sender, const std::string& path, const std::string& linkName);

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
		std::string				m_doubleFormat;
		std::string				m_integerFormat;

		class StoredContainerData {
			public:
				StoredContainerData(const std::string& linkName,
						    Datapoint *dp,
						    const std::string& format,
						    OMFHints *hints) :
							m_linkName(linkName),
							m_dp(dp), m_format(format)
				{
							if (hints)
							{
								m_hints = new OMFHints(hints->getRawHint());
							}
							else
							{
								m_hints = NULL;
							}
				};
				~StoredContainerData()
				{
					delete m_hints;
				}
				std::string	m_linkName;
				std::string	m_format;
				Datapoint	*m_dp;
				OMFHints	*m_hints;
		};

		/**
		 * A vector of data points and link_names sent in the last set
		 * of container messages. This is used to do error recovery of
		 * contianer messages.
		 */
		std::vector<StoredContainerData *>	m_containerDatapoints;
};
#endif
