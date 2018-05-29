/*
 * FogLAMP category management
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <config_category.h>
#include <string>
#include <rapidjson/document.h>
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

ConfigCategory::~ConfigCategory()
{
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{
		delete *it;
	}
}

bool ConfigCategory::itemExists(const string& name) const
{
	for (int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return true;
		}
	}
	return false;
}

string ConfigCategory::getValue(const string& name) const
{
	for (int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_value;
		}
	}
	throw new exception;
}

void ConfigCategory::setDescription(const string& description)
{
	m_description = description;
}

string ConfigCategory::toJSON() const
{
ostringstream convert;

	convert << "{ \"key\" : \"" << m_name << "\", ";
	convert << "\"description\" : \"" << m_description << "\", ";
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
	if (item.HasMember("value"))
		m_value = item["value"].GetString();
	else
		m_value = "";
	if (item.HasMember("default"))
		m_default = item["default"].GetString();
	else
		m_default = "";
}

string ConfigCategory::CategoryItem::toJSON() const
{
ostringstream convert;

	convert << "\"" << m_name << "\" : { ";
	convert << "\"description\" : \"" << m_description << "\", ";
	convert << "\"type\" : \"" << m_type << "\", ";
	convert << "\"value\" : \"" << m_value << "\", ";
	convert << "\"default\" : \"" << m_default << "\" }";
	return convert.str();
}
