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
#include <algorithm>

#include <omflinkeddata.h>
#include <omferror.h>

using namespace std;

/**
 * Create a comma-separated string of all Datapoint names in a Reading
 *
 * @param reading	Reading
 * @return			Datapoint names in the Reading
 */
static std::string DataPointNamesAsString(const Reading& reading)
{
	std::string dataPointNames;

	for (Datapoint *datapoint : reading.getReadingData())
	{
		dataPointNames.append(datapoint->getName());
		dataPointNames.append(",");
	}

	if (dataPointNames.size() > 0)
	{
		dataPointNames.resize(dataPointNames.size() - 1);	// remove trailing comma
	}

	return dataPointNames;
}

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
				string hintValue = (*it)->getHint();
				Logger::getLogger()->info("Using OMF TagName hint: %s for asset %s",
					       hintValue.c_str(), assetName.c_str());
				assetName = hintValue;
			}
			if (typeid(**it) == typeid(OMFTagHint))
			{
				string hintValue = (*it)->getHint();
				Logger::getLogger()->info("Using OMF Tag hint: %s for asset %s",
					       hintValue.c_str(), assetName.c_str());
				assetName = hintValue;
			}
		}
	}


	// Get reading data
	const vector<Datapoint*> data = reading.getReadingData();
	vector<string> skippedDatapoints;

	Logger::getLogger()->debug("Processing %s (%s) using Linked Types", assetName.c_str(), DataPointNamesAsString(reading).c_str());

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
			skippedDatapoints.push_back(dpName);
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
			string baseType = getBaseType(*it, format);
			auto container = m_containerSent->find(link);
			if (container == m_containerSent->end())
			{
				sendContainer(link, *it, hints, baseType);
				m_containerSent->insert(pair<string, string>(link, baseType));
			}
			else if (baseType.compare(container->second) != 0)
			{
				if (container->second.compare(0, 6, "Double") == 0 &&
						(baseType.compare(0, 7, "Integer") == 0
						 || baseType.compare(0, 8, "UInteger") == 0))
				{
					string msg = "Asset " + assetName + " data point " + dpName 
				       		+ " conversion from floating point to integer is being ignored";
					OMF::reportAsset(assetName, "warn", msg);
					baseType = container->second;
				}
				else
				{
					sendContainer(link, *it, hints, baseType);
					(*m_containerSent)[link] = baseType;
				}
			}
			if (baseType.empty())
			{
				// Type is not supported, skip the datapoint
				skippedDatapoints.push_back(dpName);
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
	if (skippedDatapoints.size() > 0)
	{
		string points;
		for (string& dp : skippedDatapoints)
		{
			if (!points.empty())
				points.append(", ");
			points.append(dp);
		}
		auto pos = points.find_last_of(",");
		if (pos != string::npos)
		{
			points.replace(pos, 1, " and");
		}
		string assetName = reading.getAssetName();
		string msg = "The asset " + assetName + " had a number of datapoints, " + points + " that are not supported by OMF and have been omitted";
		OMF::reportAsset(assetName, "warn", msg);
	}
	Logger::getLogger()->debug("Created data messages %s", outData.c_str());
	return outData;
}

/**
 * Calculate the base type we need to link the container
 *
 * @param dp		The datapoint to process
 * @param format	The format to use based on a hint, this may be empty
 * @return	The base type linked in the container
 */
string OMFLinkedData::getBaseType(Datapoint *dp, const string& format)
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
			Logger::getLogger()->error("Unsupported type %s for the data point %s", dp->getData().getTypeStr(),
					dp->getName().c_str());
			// Not supported
			return baseType;
	}
	return baseType;
}

/**
 * Send the container message for the linked datapoint
 *
 * @param linkName	The name to use for the container
 * @param dp		The datapoint to process
 * @param hints		Hints related to this asset
 * @param baseType	The baseType we will use
 */
void OMFLinkedData::sendContainer(string& linkName, Datapoint *dp, OMFHints * hints, const string& baseType)
{
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
			Logger::getLogger()->error("An error occurred sending the container data. HTTP code %d - %s %s",
						   res,
						   sender.getHostPort().c_str(),
						   sender.getHTTPResponse().c_str());
			return false;
		}
	}
	// Exception raised for HTTP 400 Bad Request
	catch (const BadRequest& e)
	{
		OMFError error(sender.getHTTPResponse());
		if (error.hasErrors())
		{
			Logger::getLogger()->warn("The OMF endpoint reported a bad request when sending containers: %d messages",
					error.messageCount());
			for (unsigned int i = 0; i < error.messageCount(); i++)
			{
				Logger::getLogger()->warn("Message %d: %s, %s, %s",
						i, error.getEventSeverity(i).c_str(), error.getMessage(i).c_str(), error.getEventReason(i).c_str());
			}
		}

		return error.hasErrors();
	}
	catch (const Conflict& e)
	{
		OMFError error(sender.getHTTPResponse());
		// The following is possibly too verbose
		if (error.hasErrors())
		{
			Logger::getLogger()->warn("The OMF endpoint reported a conflict when sending containers: %d messages",
					error.messageCount());
			for (unsigned int i = 0; i < error.messageCount(); i++)
			{
				string severity = error.getEventSeverity(i);
				if (severity.compare("Error") == 0)
				{
					Logger::getLogger()->warn("Message %d: %s, %s, %s",
						i, error.getEventSeverity(i).c_str(), error.getMessage(i).c_str(), error.getEventReason(i).c_str());
				}
			}
		}

		return error.hasErrors();
	}
	catch (const std::exception& e)
	{

		Logger::getLogger()->error("An exception occurred when sending container information the OMF endpoint, %s - %s %s",
									e.what(),
									sender.getHostPort().c_str(),
									path.c_str());
		return false;
	}
	return true;
}
