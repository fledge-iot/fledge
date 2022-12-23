/*
 * Fledge OSIsoft OMF interface to PI Server.
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

#include <utility>
#include <iostream>
#include <string>
#include <cstring>
#include <omf.h>
#include <OMFHint.h>
#include <logger.h>
#include "string_utils.h"
#include <datapoint.h>

#include <iterator>
#include <typeinfo>

#include <omflinkeddata.h>

using namespace std;
/**
 * OMFLinkedData constructor, generates the OMF message containing the data
 *
 * @param reading           Reading for which the OMF message must be generated
 * @param AFHierarchyPrefix Unused at the current stage
 * @param hints             OMF hints for the specific reading for changing the behaviour of the operation
 *
 */
string OMFLinkedData::processReading(const Reading& reading, const string&  AFHierarchyPrefix, OMFHints *hints)
{
	string outData;
	bool changed;


	string assetName = reading.getAssetName();
	// Apply any TagName hints to modify the containerid
	if (hints)
	{
		const std::vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.cend(); it++)
		{
			if (typeid(**it) == typeid(OMFTagNameHint))
			{
				assetName = (*it)->getHint();
				Logger::getLogger()->info("Using OMF TagName hint: %s", assetName.c_str());
			}
			if (typeid(**it) == typeid(OMFTagHint))
			{
				assetName = (*it)->getHint();
				Logger::getLogger()->info("Using OMF Tag hint: %s", assetName.c_str());
			}
		}
	}


	// Get reading data
	const vector<Datapoint*> data = reading.getReadingData();
	unsigned long skipDatapoints = 0;

	Logger::getLogger()->info("Processing %s with new OMF method", assetName.c_str());

	bool needDelim = false;
	if (m_assetSent->find(assetName) == m_assetSent->end())
	{
		// Send the data message to create the asset instance
		outData.append("{ \"typeid\":\"FledgeAsset\", \"values\":[ { \"AssetId\":\"");
		outData.append(assetName + "\",\"Name\":\"");
            	outData.append(assetName + "\"");
         	outData.append("} ] }");
		needDelim = true;
		m_assetSent->insert(pair<string, bool>(assetName, true));
	}

	/**
	 * This loop creates the data values for each of the datapoints in the
	 * reading.
	 */
	for (vector<Datapoint*>::const_iterator it = data.begin(); it != data.end(); ++it)
	{
		string dpName = (*it)->getName();
		if (dpName.compare(OMF_HINT) == 0)
		{
			// Don't send the OMF Hint to the PI Server
			continue;
		}
		if (!isTypeSupported((*it)->getData()))
		{
			skipDatapoints++;;	
			continue;
		}
		else
		{
			if (needDelim)
			{
				outData.append(",");
			}
			else
			{
				needDelim = true;
			}
			string format;
			if (hints)
			{
				const vector<OMFHint *> omfHints = hints->getHints(dpName);
				for (auto hit = omfHints.cbegin(); hit != omfHints.cend(); hit++)
				{
					if (typeid(**hit) == typeid(OMFNumberHint))
					{
						format = (*hit)->getHint();
						break;
					}
					if (typeid(**hit) == typeid(OMFIntegerHint))
					{
						format = (*hit)->getHint();
						break;
					}

				}
			}

			// Create the link for the asset if not already created
			string link = assetName + "." + dpName;
			string baseType;
			auto container = m_containerSent->find(link);
			if (container == m_containerSent->end())
			{
				baseType = sendContainer(link, *it, format, hints);
				m_containerSent->insert(pair<string, string>(link, baseType));
			}
			else
			{
				baseType =  container->second;
			}
			if (baseType.empty())
			{
				// Type is not supported, skip the datapoint
				continue;
			}
			if (m_linkSent->find(link) == m_linkSent->end())
			{
				outData.append("{ \"typeid\":\"__Link\",");
				outData.append("\"values\":[ { \"source\" : {");
				outData.append("\"typeid\": \"FledgeAsset\",");
				outData.append("\"index\":\"" + assetName);
				outData.append("\" }, \"target\" : {");
				outData.append("\"containerid\" : \"");
				outData.append(link);
				outData.append("\" } } ] },");

				m_linkSent->insert(pair<string, bool>(link, true));
			}

			// Convert reading data into the OMF JSON string
			outData.append("{\"containerid\": \"" + link);
			outData.append("\", \"values\": [{");

			// Base type we are using for this data point
			outData.append("\"" + baseType + "\": ");
			// Add datapoint Value
		       	outData.append((*it)->getData().toString());
			outData.append(", ");
			// Append Z to getAssetDateTime(FMT_STANDARD)
			outData.append("\"Time\": \"" + reading.getAssetDateUserTime(Reading::FMT_STANDARD) + "Z" + "\"");
			outData.append("} ] }");
		}
	}
	Logger::getLogger()->debug("Created data messasges %s", outData.c_str());
	return outData;
}

/**
 * Send the container message for the linked datapoint
 *
 * @param linkName	The name to use for the container
 * @param dp		The datapoint to process
 * @param format	The format to use based on a hint, this may be empty
 * @param hints		Hints related to this asset
 * @return	The base type linked in the container
 */
string OMFLinkedData::sendContainer(string& linkName, Datapoint *dp, const string& format, OMFHints * hints)
{
	string baseType;
	switch (dp->getData().getType())
	{
		case DatapointValue::T_STRING:
			baseType = "String";
			break;
		case DatapointValue::T_INTEGER:
		{
			string intFormat;
			if (!format.empty())
				intFormat = format;
			else
				intFormat = m_integerFormat;
			if (intFormat.compare("int64") == 0)
				baseType = "Integer64";
			else if (intFormat.compare("int32") == 0)
				baseType = "Integer32";
			else if (intFormat.compare("int16") == 0)
				baseType = "Integer16";
			else if (intFormat.compare("uint64") == 0)
				baseType = "UInteger64";
			else if (intFormat.compare("uint32") == 0)
				baseType = "UInteger32";
			else if (intFormat.compare("uint16") == 0)
				baseType = "UInteger16";
			break;
		}
		case DatapointValue::T_FLOAT:
		{
			string doubleFormat;
			if (!format.empty())
				doubleFormat = format;
			else
				doubleFormat = m_doubleFormat;
			if (doubleFormat.compare("float64") == 0)
				baseType = "Double64";
			else if (doubleFormat.compare("float32") == 0)
				baseType = "Double32";
			break;
		}
		default:
			Logger::getLogger()->error("Unsupported type %s", dp->getData().getTypeStr());
			// Not supported
			return baseType;
	}

	string dataSource = "Fledge";
	string uom, minimum, maximum, interpolation;
	bool propertyOverrides = false;


	if (hints)
	{
		const vector<OMFHint *> omfHints = hints->getHints();
		for (auto it = omfHints.cbegin(); it != omfHints.end(); it++)
		{
			if (typeid(**it) == typeid(OMFSourceHint))
			{
				dataSource = (*it)->getHint();
			}
		}

		const vector<OMFHint *> dpHints = hints->getHints(dp->getName());
		for (auto it = dpHints.cbegin(); it != dpHints.end(); it++)
		{
			if (typeid(**it) == typeid(OMFSourceHint))
			{
				dataSource = (*it)->getHint();
			}
			if (typeid(**it) == typeid(OMFUOMHint))
			{
				uom = (*it)->getHint();
				propertyOverrides = true;
			}
			if (typeid(**it) == typeid(OMFMinimumHint))
			{
				minimum = (*it)->getHint();
				propertyOverrides = true;
			}
			if (typeid(**it) == typeid(OMFMaximumHint))
			{
				maximum = (*it)->getHint();
				propertyOverrides = true;
			}
			if (typeid(**it) == typeid(OMFInterpolationHint))
			{
				interpolation = (*it)->getHint();
				propertyOverrides = true;
			}
		}
	}
	
	string container = "{ \"id\" : \"" + linkName;
	container += "\", \"typeid\" : \"";
	container += baseType;
	container += "\", \"name\" : \"";
	container += dp->getName();
	container += "\", \"datasource\" : \"" + dataSource + "\"";

	if (propertyOverrides)
	{
		container += ", \"propertyoverrides\" : { \"";
		container += baseType;
		container += "\" : {";
		string delim = "";
		if (!uom.empty())
		{
			delim = ",";
			container += "\"uom\" : \"";
			container += uom;
			container += "\"";
		}
		if (!minimum.empty())
		{
			container += delim;
			delim = ",";
			container += "\"minimum\" : ";
			container += minimum;
		}
		if (!maximum.empty())
		{
			container += delim;
			delim = ",";
			container += "\"maximum\" : ";
			container += maximum;
		}
		if (!interpolation.empty())
		{
			container += delim;
			delim = ",";
			container += "\"interpolation\" : \"";
			container += interpolation;
			container += "\"";
		}
		container += "} }";
	}
	container += "}";

	Logger::getLogger()->debug("Built container: %s", container.c_str());

	if (! m_containers.empty())
		m_containers += ",";
	m_containers.append(container);

	return baseType;
}

/**
 * Flush the container definitions that have been built up
 *
 * @return 	true if the containers where succesfully flushed
 */
bool OMFLinkedData::flushContainers(HttpSender& sender, const string& path, vector<pair<string, string> >& header)
{
	if (m_containers.empty())
		return true;		// Nothing to flush
	string payload = "[" + m_containers + "]";
	m_containers = "";

	Logger::getLogger()->debug("Flush container information: %s", payload.c_str());

	// Write to OMF endpoint
	try
	{
		int res = sender.sendRequest("POST",
					   path,
					   header,
					   payload);
		if  ( ! (res >= 200 && res <= 299) )
		{
			Logger::getLogger()->error("Sending containers, HTTP code %d - %s %s",
						   res,
						   sender.getHostPort().c_str(),
						   path.c_str());
			return false;
		}
	}
	// Exception raised for HTTP 400 Bad Request
	catch (const BadRequest& e)
	{

		Logger::getLogger()->warn("Sending containers, not blocking issue: %s - %s %s",
				e.what(),
				sender.getHostPort().c_str(),
				path.c_str());

		return false;
	}
	catch (const std::exception& e)
	{

		Logger::getLogger()->error("Sending containers, %s - %s %s",
									e.what(),
									sender.getHostPort().c_str(),
									path.c_str());
		return false;
	}
	return true;
}
