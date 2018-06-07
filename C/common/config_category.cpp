/*
 * FogLAMP category management
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <config_category.h>
#include <string>
#include <rapidjson/document.h>
#include <rapidjson/ostreamwrapper.h>
#include <rapidjson/writer.h>
#include <sstream>
#include <iostream>
#include <time.h>
#include <stdlib.h>

using namespace std;
using namespace rapidjson;

/**
 * Construct a ConfigCategories object from a JSON document returned from
 * the FogLAMP configuratrion service.
 */
ConfigCategories::ConfigCategories(const std::string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		throw new exception();
	}
	if (doc.HasMember("categories"))
	{
		const Value& categories = doc["categories"];
		if (categories.IsArray())
		{
			// Process every rows and create the result set
			for (auto& cat : categories.GetArray())
			{
				if (!cat.IsObject())
				{
					throw new exception();
				}
				ConfigCategoryDescription *value = new ConfigCategoryDescription(cat["key"].GetString(),
							cat["description"].GetString());
				m_categories.push_back(value);
			}
		}
		else
		{
			throw new exception();
		}
	}
}

/**
 * ConfigCategories destructor
 */
ConfigCategories::~ConfigCategories()
{
	for (auto it = m_categories.cbegin(); it != m_categories.cend(); it++)
	{
		delete *it;
	}
}

/**
 * Configuration Category constructor
 *
 * @param name	The name of the configuration category
 * @param json	JSON content of the configuration category
 */
ConfigCategory::ConfigCategory(const string& name, const string& json) : m_name(name)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		throw new exception();
	}
	for (Value::ConstMemberIterator itr = doc.MemberBegin(); itr != doc.MemberEnd(); ++itr)
	{
		m_items.push_back(new CategoryItem(itr->name.GetString(), itr->value));
	}
}

/**
 * Configuration category destructor
 */
ConfigCategory::~ConfigCategory()
{
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{
		delete *it;
	}
}

/**
 * Check for the existance of an item within the configuration category
 *
 * @param name	Item name to check within the category
 */
bool ConfigCategory::itemExists(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return true;
		}
	}
	return false;
}

/**
 * Return the value of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getValue(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_value;
		}
	}
	throw new exception;
}

/**
 * Return the type of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getType(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_type;
		}
	}
	throw new exception;
}

/**
 * Return the description of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getDescription(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_description;
		}
	}
	throw new exception;
}

/**
 * Return the default value of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getDefault(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_default;
		}
	}
	throw new exception;
}

/**
 * Return if the configuration item is a string item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a string type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isString(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_itemType == CategoryItem::StringItem;
		}
	}
	throw new exception;
}

/**
 * Return if the configuration item is a JSON item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a JSON type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isJSON(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_itemType == CategoryItem::JsonItem;
		}
	}
	throw new exception;
}

/**
 * Set the description for the configuration category
 *
 * @param description	The configuration category description
 */
void ConfigCategory::setDescription(const string& description)
{
	m_description = description;
}

/**
 * Return JSON string of all category components
 */
string ConfigCategory::toJSON() const
{
ostringstream convert;

	convert << "{ \"key\" : \"" << m_name << "\", ";
	convert << "\"description\" : \"" << m_description << "\", \"value\" : ";
	// Add items
	convert << ConfigCategory::itemsToJSON();
	convert << " }";

	return convert.str();
}

/**
 * Return JSON string of category items only
 */
string ConfigCategory::itemsToJSON() const
{
ostringstream convert;

	convert << "{";
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{
		convert << (*it)->toJSON();
		if (it + 1 != m_items.cend() )
		{
			convert << ", ";
		}
	}
	convert << "}";

	return convert.str();
}

/**
 * Constructor for a configuration item
 */
ConfigCategory::CategoryItem::CategoryItem(const string& name, const Value& item)
{
	m_name = name;
	if (! item.IsObject())
	{
		throw new exception();
	}
	if (item.HasMember("type"))
		m_type = item["type"].GetString();
	else
		m_type = "";
	if (item.HasMember("description"))
		m_description = item["description"].GetString();
	else
		m_description = "";
	if (item.HasMember("value") && item["value"].IsString())
	{
		m_value = item["value"].GetString();
		m_itemType = StringItem;
	}
	else if (item.HasMember("value") && item["value"].IsObject())
	{
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["value"].Accept(writer);
		m_value = strbuf.GetString();
		m_itemType = JsonItem;
	}
	else
	{
		m_value = "";
	}
	if (item.HasMember("default") && item["default"].IsString())
	{
		m_default = item["default"].GetString();
		m_itemType = StringItem;
	}
	else if (item.HasMember("default") && item["default"].IsObject())
	{
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["default"].Accept(writer);
		m_default = strbuf.GetString();
		m_itemType = JsonItem;
	}
	else
		m_default = "";
}

/**
 * Create a JSON representation of the configuration item
 */
string ConfigCategory::CategoryItem::toJSON() const
{
ostringstream convert;

	convert << "\"" << m_name << "\" : { ";
	convert << "\"description\" : \"" << m_description << "\", ";
	convert << "\"type\" : \"" << m_type << "\", ";
	if (m_itemType == StringItem)
	{
		convert << "\"value\" : \"" << m_value << "\", ";
		convert << "\"default\" : \"" << m_default << "\" }";
	}
	else if (m_itemType == JsonItem)
	{
		convert << "\"value\" : " << m_value << ", ";
		convert << "\"default\" : " << m_default << " }";
	}
	return convert.str();
}

/**
 * Return only "default" item values
 */
string ConfigCategory::CategoryItem::defaultToJSON() const
{
ostringstream convert;

	convert << "\"" << m_name << "\" : { ";
	convert << "\"description\" : \"" << m_description << "\", ";
	convert << "\"type\" : \"" << m_type << "\", ";
	if (m_itemType == StringItem)
	{
		convert << "\"default\" : \"" << m_default << "\" }";
	}
	else if (m_itemType == JsonItem)
	{
		convert << "\"default\" : " << m_default << " }";
	}
	return convert.str();
}

// DefaultConfigCategory constructor
DefaultConfigCategory::DefaultConfigCategory(const string& name, const string& json) :
                                            ConfigCategory::ConfigCategory(name, json)
{
}

/**
 * Return JSON string of all category components
 * of a DefaultConfigCategory class
 */
string DefaultConfigCategory::toJSON() const
{
ostringstream convert;

	convert << "{ ";
	convert << "\"key\" : \"" << m_name << "\", ";
	convert << "\"description\" : \"" << m_description << "\", \"value\" : ";
	// Add items
	convert << DefaultConfigCategory::itemsToJSON();
	convert << " }";

	return convert.str();
}

/**
 * Return DefaultConfigCategory "default" items only
 */
string DefaultConfigCategory::itemsToJSON() const
{
ostringstream convert;
        
	convert << "{ ";
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{       
		convert << (*it)->defaultToJSON();
		if (it + 1 != m_items.cend() )
		{       
			convert << ", ";
		}
	}
	convert << " }";

	return convert.str();
}
