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
#include <omfbuffer.h>
#include <linkedlookup.h>

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
		OMFLinkedData(  std::unordered_map<std::string, LALookup> *linkedAssetState,
				const OMF_ENDPOINT PIServerEndpoint = ENDPOINT_CR) :
					m_linkedAssetState(linkedAssetState),
					m_endpoint(PIServerEndpoint),
       					m_doubleFormat("float64"),
					m_integerFormat("int64")
					{};
		bool		processReading(OMFBuffer& payload, bool needDelim, const Reading& reading,
				const std::string& DefaultAFLocation = std::string(),
				OMFHints *hints = NULL);
		void		buildLookup(const std::vector<Reading *>& reading);
		void		setSendFullStructure(const bool sendFullStructure) {m_sendFullStructure = sendFullStructure;};
		bool		flushContainers(HttpSender& sender, const std::string& path, std::vector<std::pair<std::string, std::string> >& header);
		void		setDelimiter(const std::string &delimiter) {m_delimiter = delimiter;};
		void		setFormats(const std::string& doubleFormat, const std::string& integerFormat)
				{
					m_doubleFormat = doubleFormat;
					m_integerFormat = integerFormat;
				};
	private:
		std::string	getBaseType(Datapoint *dp, const std::string& format);
		void		sendContainer(std::string& link, Datapoint *dp, OMFHints * hints, const std::string& baseType);
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
		bool m_sendFullStructure;
		std::string m_delimiter;

		/**
		 * The container for this asset and data point has been sent in
		 * this session. The key is the asset followed by the datapoint name
		 * with a delimiter (default: '.') in between. The value is the base type used, a
		 * container will be sent if the base type changes.
		 */
		std::unordered_map<std::string, LALookup>	*m_linkedAssetState;

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

};
#endif
