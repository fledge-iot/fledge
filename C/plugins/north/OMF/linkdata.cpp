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
#include <rapidjson/document.h>
#include "rapidjson/error/en.h"

#include <omflinkeddata.h>

#include <stdio.h>

using namespace std;
using namespace rapidjson;

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
			// Not supported
			Logger::getLogger()->error("Unsupported type %s", dp->getData().getTypeStr());
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

	// Store the datapoint this message is for in case we need to take recovery action
	m_containerDatapoints.push_back(new StoredContainerData(linkName, dp, format, hints));

	return baseType;
}

/**
 * Flush the container definitions that have been built up
 *
 * @param sender	The connection on whichto send container data
 * @param path		The path used for the HTTP request
 * @param header	The header for the message
 * @param noRecovery	Set to true if we shoudl not try to recover from errors
 * @return bool 	true if the containers where succesfully flushed
 */
bool OMFLinkedData::flushContainers(HttpSender& sender, const string& path, vector<pair<string, string> >& header, bool noRecovery)
{
	bool rval = true;

	if (m_containers.empty())
		return true;		// Nothing to flush
	string payload = "[" + m_containers + "]";
	m_containers = "";

	Logger::getLogger()->info("Flush container information: %s", payload.c_str());

	string *response = new string();


	// Write to OMF endpoint
	try
	{
		int res = sender.sendRequest("POST",
					   path,
					   header,
					   payload,
					   response);
		if  ( ! (res >= 200 && res <= 299) )
		{
			Logger::getLogger()->error("Flush Containers, HTTP error code %d - %s %s %s",
						   res,
						   sender.getHostPort().c_str(),
						   path.c_str(),
						   response->c_str());
			if (noRecovery)
			{
				rval = false;
			}
			else
			{
				rval = recoverContainerError(sender, path, *response);
			}
		}
	}
	// Exception raised for HTTP 400 Bad Request
	catch (const BadRequest& e)
	{

		Logger::getLogger()->warn("Sending containers, not blocking issue: %s - %s %s",
				e.what(),
				sender.getHostPort().c_str(),
				path.c_str());

		rval = false;
	}
	catch (const Conflict& e)
	{
		Logger::getLogger()->error("Conflict Sending containers, %s - %s %s",
									e.what(),
									sender.getHostPort().c_str(),
									path.c_str());
		if (noRecovery)
		{
			rval = false;
		}
		else
		{
			string response = e.what();
			rval = recoverContainerError(sender, path, response);
		}
	}
	catch (const std::exception& e)
	{
		Logger::getLogger()->error("Sending containers, %s - %s %s",
									e.what(),
									sender.getHostPort().c_str(),
									path.c_str());
		if (! response->empty())
		{
			if (noRecovery)
			{
				rval = false;
			}
			else
			{
				rval = recoverContainerError(sender, path, *response);
			}
		}
		else
		{
			rval = false;
		}
	}

	// Don't clear the container data if we are doing recovery
	if (!noRecovery)
	{
		m_containerDatapoints.clear();
	}
	delete response;
	return rval;
}

/**
 * Attempt to recover from a failed send of the container information.
 * We pick out the failed datapoints and resend them as update messages
 * as opposed to create messages.
 *
 * @param sender	The connection to send on
 * @param path		The URL path to send to OMF
 * @param response	The error message from the OMF endpoint
 * @return bool		Return true if the updates suceeded
 */
bool OMFLinkedData::recoverContainerError(HttpSender& sender, const string& path, string& response)
{
	Document doc;
	bool	rval = true;

	Logger::getLogger()->info("Attempting container recovery with %s", response.c_str());

	size_t pos;
	while ((pos = response.find("\r")) != string::npos)
	{
		response[pos] = ' ';
	}

	if ((pos = response.find("{")) != string::npos && pos > 0)
	{
		response.erase(0, pos);
	}

	doc.Parse(response.c_str());
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("Failed to parse error response for server: %s", response.c_str());
		Logger::getLogger()->error("Error(offset %u): %s", (unsigned)doc.GetErrorOffset(),
		        GetParseError_En(doc.GetParseError()));
		return false;
	}
	if (doc.HasMember("Messages") && doc["Messages"].IsArray())
	{
		const Value& messages = doc["Messages"];
		for (rapidjson::SizeType i = 0; i < messages.Size(); i++)
		{
			const Value& message = messages[i];
			if (message.IsObject() && message.HasMember("Events"))
			{
				const Value& events = message["Events"];
				for (rapidjson::SizeType i = 0; i < events.Size(); i++)
				{
					const Value& event = events[i];
					if (event.IsObject() && event.HasMember("Severity") && event["Severity"].IsString())
					{
						string severity = event["Severity"].GetString();
						if (severity.compare("Error") == 0)
						{
							const Value& eventInfo = event["EventInfo"];
							if (eventInfo.HasMember("Parameters"))
							{
								const Value& parameters = eventInfo["Parameters"];
								string containerId;
								for (rapidjson::SizeType i = 0; i < parameters.Size(); i++)
								{
									if (parameters[i].IsObject())
									{
										string parameter = parameters[i]["Name"].GetString();
										if (parameter.compare("Container.Id") == 0)
										{
											containerId = parameters[i]["Value"].GetString();
										}
									}
								}
								// Try recovering the error
								if (!containerId.empty())
								{
									rval = recoverContainer(sender, path, containerId);
									if (!rval)
									{
										return rval;
									}
								}
								else
								{
									Logger::getLogger()->error("Failed to find container ID in error");
								}
							}
							else
							{
								Logger::getLogger()->error("Failed to find Parameters in OMF response");
							}
						}
					}
					else
					{
						Logger::getLogger()->error("Failed to find severity in OMF response");
					}
				}
			}
			else
			{
				Logger::getLogger()->error("Failed to find Events in OMF response");
			}
		}
	}
	else
	{
		Logger::getLogger()->error("Failed to find messages in OMF response");
	}

	return rval;
}

/**
 * Send a container message again as an update rather than a create action
 *
 * @param sender	The HTTP sender class to talk to the OMF endpoint
 * @param path		The URL path
 * @param linkName	The linkName which matches the containerID we are recovering
 * @return bool		True if the update succeeded
 */
bool OMFLinkedData::recoverContainer(HttpSender& sender, const string& path, const string& linkName)
{
	std::vector<std::pair<std::string, std::string> > header;

	header.push_back(pair<string, string>("messagetype", "container"));
	header.push_back(pair<string, string>("omfversion", "1.2"));
	header.push_back(pair<string, string>("messageformat", "JSON"));
	header.push_back(pair<string, string>("action", "update"));

	int i;
	for (i = 0; i < m_containerDatapoints.size(); i++)
	{
		StoredContainerData *scd = m_containerDatapoints[i];
		if (scd->m_linkName.compare(linkName) == 0)
		{
			Logger::getLogger()->debug("Send update message %s", m_containers.c_str());
			sendContainer(scd->m_linkName, scd->m_dp, scd->m_format, scd->m_hints);
			return flushContainers(sender, path, header, true);
		}
	}
	Logger::getLogger()->error("Failed to find container datapoint %s in order to create update message",
			linkName.c_str());
	return false;
}
