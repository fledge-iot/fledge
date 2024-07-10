/*
 * Fledge category management
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
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"
#include <sstream>
#include <iostream>
#include <time.h>
#include <stdlib.h>
#include <logger.h>
#include <stdexcept>
#include <string_utils.h>


using namespace std;
using namespace rapidjson;

/**
 * ConfigCategories constructor without parameters
 *
 * Elements can be added with ConfigCategories::addCategoryDescription
 */
ConfigCategories::ConfigCategories()
{
}

/**
 * Construct a ConfigCategories object from a JSON document returned from
 * the Fledge configuratrion service.
 */
ConfigCategories::ConfigCategories(const std::string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("Configuration parse error in %s: %s at %d, '%s'", json.c_str(),
			GetParseError_En(doc.GetParseError()), (unsigned)doc.GetErrorOffset(), StringAround(json, (unsigned)doc.GetErrorOffset()).c_str());
		throw new ConfigMalformed();
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
					throw new ConfigMalformed();
				}
				ConfigCategoryDescription *value = new ConfigCategoryDescription(cat["key"].GetString(),
							cat["description"].GetString());
				m_categories.push_back(value);
			}
		}
		else
		{
			throw new ConfigMalformed();
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
 * Add a ConfigCategoryDescription element
 *
 * @param  elem    The ConfigCategoryDescription elemen to add
 */
void ConfigCategories::addCategoryDescription(ConfigCategoryDescription* elem)
{
	m_categories.push_back(elem);
}

/**
 * Return the JSON string of a ConfigCategoryDescription element
 */
string ConfigCategoryDescription::toJSON() const
{
	ostringstream convert;

	convert << "{\"key\": \"" << JSONescape(m_name) << "\", ";
	convert << "\"description\" : \"" << JSONescape(m_description) << "\"}";

	return convert.str();
}

/**
 * Return the JSON string of all ConfigCategoryDescription
 * elements in m_categories
 */
string ConfigCategories::toJSON() const
{
	ostringstream convert;

	convert << "[";
	for (auto it = m_categories.cbegin(); it != m_categories.cend(); it++)
	{
		convert << (*it)->toJSON();
		if (it + 1 != m_categories.cend() )
		{
                        convert << ", ";
		}
	}
	convert << "]";

	return convert.str();
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
		Logger::getLogger()->error("Configuration parse error in category '%s', %s: %s at %d, '%s'",
			name.c_str(), json.c_str(),
			GetParseError_En(doc.GetParseError()), (unsigned)doc.GetErrorOffset(),
			StringAround(json, (unsigned)doc.GetErrorOffset()).c_str());
		throw new ConfigMalformed();
	}
	
	for (Value::ConstMemberIterator itr = doc.MemberBegin(); itr != doc.MemberEnd(); ++itr)
	{
		try
		{
			m_items.push_back(new CategoryItem(itr->name.GetString(), itr->value));
		}
		catch (exception* e)
		{
			Logger::getLogger()->error("Configuration parse error in category '%s' item '%s', %s: %s",
				name.c_str(),
				itr->name.GetString(),
				json.c_str(),
				e->what());
			delete e;
			throw ConfigMalformed();
		}
		catch (...)
		{
			throw;
		}
	}
}

/**
 * Copy constructor for a configuration category
 */
ConfigCategory::ConfigCategory(ConfigCategory const& rhs)
{
	m_name = rhs.m_name;
	m_description = rhs.m_description;

	for (auto it = rhs.m_items.cbegin(); it != rhs.m_items.cend(); it++)
	{
		m_items.push_back(new CategoryItem(**it));
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
 * Operator= for ConfigCategory
 */
ConfigCategory& ConfigCategory::operator=(ConfigCategory const& rhs)
{
	m_name = rhs.m_name;
	m_description = rhs.m_description;

	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{
		delete *it;
	}
	m_items.clear();
	for (auto it = rhs.m_items.cbegin(); it != rhs.m_items.cend(); it++)
	{
		m_items.push_back(new CategoryItem(**it));
	}
	return *this;
}

/**
 * Operator+= for ConfigCategory
 */
ConfigCategory& ConfigCategory::operator+=(ConfigCategory const& rhs)
{
	m_name = rhs.m_name;
	m_description = rhs.m_description;

	for (auto it = rhs.m_items.cbegin(); it != rhs.m_items.cend(); it++)
	{
		m_items.push_back(new CategoryItem(**it));
	}
	return *this;
}

/**
 * Set the m_value from m_default for each item
 */
void ConfigCategory::setItemsValueFromDefault()
{
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{
		(*it)->m_value = string((*it)->m_default);
	}
}

/**
 * Check whether at least one item in the category object
 * has both 'value' and 'default' set.
 *
 * @throws ConfigValueFoundWithDefault
 */
void ConfigCategory::checkDefaultValuesOnly() const
{
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{
		if (!(*it)->m_value.empty())
		{
			throw new ConfigValueFoundWithDefault((*it)->m_name);
		}
	}
}

/**
 * Add an item to a configuration category
 */
void ConfigCategory::addItem(const std::string& name, const std::string description,
                             const std::string& type, const std::string def,
                             const std::string& value)
{
	m_items.push_back(new CategoryItem(name, description, type, def, value));
}

/**
 * Add an item to a configuration category
 */
void ConfigCategory::addItem(const std::string& name, const std::string description,
                             const std::string def, const std::string& value,
			     const vector<string> options)
{
	m_items.push_back(new CategoryItem(name, description, def, value, options));
}

/**
 * Set the display name of an item
 *
 * @param name	The item name in the category
 * @param displayName	The display name to set
 * @return true if the item was found
 */
bool ConfigCategory::setItemDisplayName(const std::string& name, const std::string& displayName)
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			m_items[i]->m_displayName = displayName;
			return true;
		}
	}
	return false;
}

/**
 * Delete all the items from the configuration category having a specific type
 *
 * * @param type  Type to delete
 */
void ConfigCategory::removeItemsType(ConfigCategory::ItemType type)
{
	for (auto it = m_items.begin(); it != m_items.end(); )
	{
		if ((*it)->m_itemType == type)
		{
			delete *it;
			m_items.erase(it);
		}
		else
		{
			++it;
		}
	}
}

/**
 * Delete all the items from the configuration category
 *
 */
void ConfigCategory::removeItems()
{
	for (auto it = m_items.begin(); it != m_items.end(); )
	{
		delete *it;
		m_items.erase(it);
	}
}

/**
 * Delete all the items from the configuration category not having a specific type
 *
 * * @param type  Type to maintain
 */
void ConfigCategory::keepItemsType(ConfigCategory::ItemType type)
{

	for (auto it = m_items.begin(); it != m_items.end(); )
	{
		if ((*it)->m_itemType != type)
		{
			delete *it;
			m_items.erase(it);
		}
		else
		{
			++it;
		}
	}
}

/**
 * Extracts, process and adds subcategory information from a given category to the current instance
 *
 * * @param subCategories Configuration category from which the subcategories information should be extracted
 */
bool ConfigCategory::extractSubcategory(ConfigCategory &subCategories)
{

	bool extracted;

	auto it = subCategories.m_items.begin();

	if (it != subCategories.m_items.end())
	{
		// Generates a new temporary category from the JSON in m_default
		ConfigCategory tmpCategory = ConfigCategory("tmpCategory", (*it)->m_default);

		// Extracts all the items generated from m_default and adds them to the category
		for(auto item : tmpCategory.m_items)
		{

			m_items.push_back(new CategoryItem(*item));
		}

		m_name = (*it)->m_name;
		m_description = (*it)->m_description;

		// Replaces the %N escape sequence with the instance name of this plugin
		string instanceName = subCategories.m_name;
		string pattern  = "%N";

		if (m_name.find(pattern) != string::npos)
			m_name.replace(m_name.find(pattern), pattern.length(), instanceName);

		// Removes the element just processed
		delete *it;
		subCategories.m_items.erase(it);
		extracted = true;
	}
	else
	{
		extracted = false;
	}

	return 	extracted;

}

/**
 * Check for the existence of an item within the configuration category
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
	throw new ConfigItemNotFound();
}

/**
 * Return the value of the configuration category item list, this
 * is a convience function used when simple lists are defined
 * and allows for central processing of the list values
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
vector<string> ConfigCategory::getValueList(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			if (m_items[i]->m_type.compare("list"))
			{
				throw new ConfigItemNotAList();
			}
			Document d;
			vector<string> list;
			d.Parse(m_items[i]->m_value.c_str());
			if (d.HasParseError())
			{
				Logger::getLogger()->error("The JSON value for a list item %s has a parse error: %s, %s",
					name.c_str(), GetParseError_En(d.GetParseError()), m_items[i]->m_value.c_str());
				return list;
			}
			if (d.IsArray())
			{
				for (auto& v : d.GetArray())
				{
					if (v.IsString())
					{
						list.push_back(v.GetString());
					}
				}
			}
			else
			{
				Logger::getLogger()->error("The value of the list item %s should be a JSON array and it is not", name.c_str());
			}
			return list;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return the value of the configuration category item kvlist, this
 * is a convience function used when key/value lists are defined
 * and allows for central processing of the list values
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
map<string, string> ConfigCategory::getValueKVList(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			if (m_items[i]->m_type.compare("kvlist"))
			{
				throw new ConfigItemNotAList();
			}
			map<string, string> list;
			Document d;
			d.Parse(m_items[i]->m_value.c_str());
			if (d.HasParseError())
			{
				Logger::getLogger()->error("The JSON value for a kvlist item %s has a parse error: %s, %s",
					name.c_str(), GetParseError_En(d.GetParseError()), m_items[i]->m_value.c_str());
				return list;
			}
			for (auto& v : d.GetObject())
			{
				string key = v.name.GetString();
				string value = to_string(v.value);
				list.insert(pair<string, string>(key, value));
			}
			return list;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Convert a RapidJSON value to a string
 *
 * @param v	The RapidJSON value
 */
std::string ConfigCategory::to_string(const rapidjson::Value& v) const
{
	if (v.IsString())
	{
		return { v.GetString(), v.GetStringLength() };
	}
	else
	{
		StringBuffer strbuf;
		Writer<rapidjson::StringBuffer> writer(strbuf);
		v.Accept(writer);
		return { strbuf.GetString(), strbuf.GetLength() };
	}
}

/**
 * Return the requested attribute of a configuration category item
 *
 * @param name	The name of the configuration item to return
 * @param itemAttribute	The item attribute (such as "file", "order", "readonly"
 * @return	The configuration item attribute as string
 * @throws	ConfigItemNotFound if the item does not exist in the category
 *		ConfigItemAttributeNotFound if the requested attribute
 *		does not exist for the found item.
 */
string ConfigCategory::getItemAttribute(const string& itemName,
					const ItemAttribute itemAttribute) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (itemName.compare(m_items[i]->m_name) == 0)
		{
			switch (itemAttribute)
			{
				case ORDER_ATTR:
					return m_items[i]->m_order;
				case READONLY_ATTR:
					return m_items[i]->m_readonly;
				case MANDATORY_ATTR:
				    return m_items[i]->m_mandatory;
				case FILE_ATTR:
					return m_items[i]->m_file;
				case VALIDITY_ATTR:
					return m_items[i]->m_validity;
				case GROUP_ATTR:
					return m_items[i]->m_group;
				case DISPLAY_NAME_ATTR:
					return m_items[i]->m_displayName;
				case DEPRECATED_ATTR:
					return m_items[i]->m_deprecated;
				case RULE_ATTR:
					return m_items[i]->m_rule;
				case BUCKET_PROPERTIES_ATTR:
					return m_items[i]->m_bucketProperties;
				case LIST_SIZE_ATTR:
					return m_items[i]->m_listSize;
				case ITEM_TYPE_ATTR:
					return m_items[i]->m_listItemType;
				case LIST_NAME_ATTR:
				    return m_items[i]->m_listName;
				default:
					throw new ConfigItemAttributeNotFound();
			}
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Set the requested attribute of a configuration category item
 *
 * @param name	The name of the configuration item to return
 * @param itemAttribute	The item attribute (such as "file", "order", "readonly"
 * @param value	The value to set
 * @return	The configuration item attribute as string
 * @throws	ConfigItemNotFound if the item does not exist in the category
 *		ConfigItemAttributeNotFound if the requested attribute
 *		does not exist for the found item.
 */
bool ConfigCategory::setItemAttribute(const string& itemName,
					const ItemAttribute itemAttribute,
					const string& value)
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (itemName.compare(m_items[i]->m_name) == 0)
		{
			switch (itemAttribute)
			{
				case ORDER_ATTR:
					m_items[i]->m_order = value;
					return true;
				case READONLY_ATTR:
					m_items[i]->m_readonly = value;
					return true;
				case MANDATORY_ATTR:
				    m_items[i]->m_mandatory = value;
					return true;
				case FILE_ATTR:
					m_items[i]->m_file = value;
					return true;
				case MINIMUM_ATTR:
					m_items[i]->m_minimum = value;
					return true;
				case MAXIMUM_ATTR:
					m_items[i]->m_maximum = value;
					return true;
				case LENGTH_ATTR:
					m_items[i]->m_length = value;
					return true;
				case VALIDITY_ATTR:
					m_items[i]->m_validity = value;
					return true;
				case GROUP_ATTR:
					m_items[i]->m_group = value;
					return true;
				case DISPLAY_NAME_ATTR:
					m_items[i]->m_displayName = value;
					return true;
				case DEPRECATED_ATTR:
					m_items[i]->m_deprecated = value;
					return true;
				case RULE_ATTR:
					m_items[i]->m_rule = value;
					return true;
				case BUCKET_PROPERTIES_ATTR:
					m_items[i]->m_bucketProperties = value;
					return true;
				case LIST_SIZE_ATTR:
					m_items[i]->m_listSize = value;
					return true;
				case ITEM_TYPE_ATTR:
					m_items[i]->m_listItemType = value;
					return true;
				case LIST_NAME_ATTR:
					m_items[i]->m_listName = value;
					return true;
				default:
					return false;
			}
		}
	}
	return false;
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
	throw new ConfigItemNotFound();
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
	throw new ConfigItemNotFound();
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
	throw new ConfigItemNotFound();
}

/**
 * Update the default value of the configuration category item
 *
 * @param name	The name of the configuration item to update
 * @param value	New value of the configuration item
 * @return bool	Whether update succeeded
 */
bool ConfigCategory::setDefault(const string& name, const string& value)
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			m_items[i]->m_default = value;
			return true;
		}
	}
	return false;
}

/**
 * Update the value of the configuration category item
 *
 * @param name	The name of the configuration item to update
 * @param value	New value of the configuration item
 * @return bool	Whether update succeeded
 */
bool ConfigCategory::setValue(const string& name, const string& value)
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			m_items[i]->m_value = value;
			return true;
		}
	}
	return false;
}


/**
 * Return the display name of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getDisplayName(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_displayName;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return the length value of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getLength(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_length;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return the minimum value of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getMinimum(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_minimum;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return the maximum of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
string ConfigCategory::getMaximum(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_maximum;
		}
	}
	throw new ConfigItemNotFound();
}



/**
 * Return the options of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return string	The configuration item name
 * @throws exception if the item does not exist in the category
 */
vector<string> ConfigCategory::getOptions(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_options;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return the permissions of the configuration category item
 *
 * @param name	The name of the configuration item to return
 * @return vector<string>	The configuration item permissions
 * @throws exception if the item does not exist in the category
 */
vector<string> ConfigCategory::getPermissions(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_permissions;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return true if the user has permission to update the named item
 *
 * @param name	The name of the configuration item to return
 * @param rolename	The name of the user role to test
 * @return bool	True if the named user can update the configuration item
 * @throws exception if the item does not exist in the category
 */
bool ConfigCategory::hasPermission(const std::string& name, const std::string& rolename) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			if (m_items[i]->m_permissions.empty())
				return true;
			for (auto& perm : m_items[i]->m_permissions)
				if (rolename.compare(perm) == 0)
					return true;
			return false;
		}
	}
	throw new ConfigItemNotFound();
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
			return m_items[i]->m_itemType == StringItem;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return if the configuration item is an enumeration item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a string type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isEnumeration(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_itemType == EnumerationItem;
		}
	}
	throw new ConfigItemNotFound();
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
			return m_items[i]->m_itemType == JsonItem;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return if the configuration item is a Bool item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a Bool type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isBool(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_itemType == BoolItem;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return if the configuration item is a Numeric item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a Numeric type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isNumber(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_itemType == NumberItem;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return if the configuration item is a Double item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a Double type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isDouble(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return m_items[i]->m_itemType == DoubleItem;
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return if the configuration item is deprecated a item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a deprecated type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isDeprecated(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return ! m_items[i]->m_deprecated.empty();
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return if the configuration item is a list item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a Numeric type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isList(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return (m_items[i]->m_type.compare("list") == 0);
		}
	}
	throw new ConfigItemNotFound();
}

/**
 * Return if the configuration item is a kvlist item
 *
 * @param name		The name of the item to test
 * @return bool		True if the item is a Numeric type
 * @throws exception	If the item was not found in the configuration category
 */
bool ConfigCategory::isKVList(const string& name) const
{
	for (unsigned int i = 0; i < m_items.size(); i++)
	{
		if (name.compare(m_items[i]->m_name) == 0)
		{
			return (m_items[i]->m_type.compare("kvlist") == 0);
		}
	}
	throw new ConfigItemNotFound();
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
 *
 * @param full	false is the deafult, true evaluates all the members of the CategoryItems
 *
 */
string ConfigCategory::toJSON(const bool full) const
{
ostringstream convert;

	convert << "{ \"key\" : \"" << JSONescape(m_name) << "\", ";
	convert << "\"description\" : \"" << JSONescape(m_description) << "\", \"value\" : ";
	// Add items
	convert << ConfigCategory::itemsToJSON(full);
	convert << " }";

	return convert.str();
}

/**
 * Return JSON string of category items only
 *
 * @param full	false is the deafult, true evaluates all the members of the CategoryItems
 *
 */
string ConfigCategory::itemsToJSON(const bool full) const
{
ostringstream convert;

	convert << "{";
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{
		convert << (*it)->toJSON(full);
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
 * @param name	The category item name
 * @param item	The item object to add
 * @throw	ConfigMalformed exception
 * @throw	runtime_error exception
 */
ConfigCategory::CategoryItem::CategoryItem(const string& name,
					   const Value& item)
{
	m_name = name;
	m_itemType = UnknownType;
	if (! item.IsObject())
	{
		throw new ConfigMalformed();
	}
	if (item.HasMember("type"))
	{
		m_type = item["type"].GetString();
	}
	else
	{
		m_type = "";
	}

	if (item.HasMember("description"))
	{
		m_description = item["description"].GetString();
	}
	else
	{
		m_description = "";
	}

	if (item.HasMember("order"))
	{
		m_order = item["order"].GetString();
	}
	else
	{
		m_order = "";
	}

	if (item.HasMember("length"))
	{
		m_length = item["length"].GetString();
	}
	else
	{
		m_length = "";
	}

	if (item.HasMember("minimum"))
	{
		m_minimum = item["minimum"].GetString();
	}
	else
	{
		m_minimum = "";
	}

	if (item.HasMember("maximum"))
	{
		m_maximum = item["maximum"].GetString();
	}
	else
	{
		m_maximum = "";
	}

	if (item.HasMember("file"))
	{
		m_file = item["file"].GetString();
	}
	else
	{
		m_file = "";
	}

	if (item.HasMember("readonly"))
	{
		m_readonly = item["readonly"].GetString();
	}
	else
	{
		m_readonly = "";
	}

	if (item.HasMember("mandatory"))
	{
		m_mandatory = item["mandatory"].GetString();
	}
	else
	{
		m_mandatory = "";
	}
	if (m_type.compare("category") == 0)
	{
		m_itemType = CategoryType;
	}
	if (m_type.compare("script") == 0)
	{
		m_itemType = ScriptItem;
	}
	if (m_type.compare("code") == 0)
	{
		m_itemType = CodeItem;
	}
	if (m_type.compare("bucket") == 0)
	{
		m_itemType = BucketItem;
	}
	if (m_type.compare("list") == 0)
	{
		m_itemType = ListItem;
	}
	if (m_type.compare("kvlist") == 0)
	{
		m_itemType = KVListItem;
	}

	if (item.HasMember("deprecated"))
	{
		m_deprecated = item["deprecated"].GetString();
	}
	else
	{
		m_deprecated = "";
	}

	if (item.HasMember("displayName"))
	{
		m_displayName = item["displayName"].GetString();
	}
	else
	{
		m_displayName = "";
	}

	if (item.HasMember("validity"))
	{
		m_validity = item["validity"].GetString();
	}
	else
	{
		m_validity = "";
	}
	if (item.HasMember("group"))
	{
		m_group = item["group"].GetString();
	}
	else
	{
		m_group = "";
	}

	if (item.HasMember("rule"))
	{
		m_rule = item["rule"].GetString();
	}
	else
	{
		m_rule = "";
	}

	if (item.HasMember("properties"))
	{
		Logger::getLogger()->debug("item['properties'].IsString()=%s, item['properties'].IsObject()=%s", 
										item["properties"].IsString()?"true":"false",
										item["properties"].IsObject()?"true":"false");

		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["properties"].Accept(writer);
		m_bucketProperties = item["properties"].IsObject() ?
			  // use current string
			  strbuf.GetString() :
			  // Unescape the string
			  JSONunescape(strbuf.GetString());

		Logger::getLogger()->debug("m_bucketProperties=%s", m_bucketProperties.c_str());
	}
	else
	{
		m_bucketProperties = "";
	}
	
	if (m_itemType == BucketItem && m_bucketProperties.empty())
	{
		throw new runtime_error("Bucket configuration item is missing the \"properties\" attribute");
	}

	if (item.HasMember("options"))
	{
		const Value& options = item["options"];
		if (options.IsArray())
		{
			for (SizeType i = 0; i < options.Size(); i++)
			{
				m_options.push_back(string(options[i].GetString()));
			}
		}
	}

	if (item.HasMember("permissions"))
	{
		const Value& permissions = item["permissions"];
		if (permissions.IsArray())
		{
			for (SizeType i = 0; i < permissions.Size(); i++)
			{
				m_permissions.push_back(string(permissions[i].GetString()));
			}
		}
	}

	if (item.HasMember("items"))
	{
		if (item["items"].IsString())
		{
			m_listItemType = item["items"].GetString();
		}
		else
		{
			throw new runtime_error("Items configuration item property is not a string");
		}
	}
	else if (m_itemType == ListItem || m_itemType == KVListItem)
	{
		throw new runtime_error("List configuration item is missing the \"items\" attribute");
	}
	if (item.HasMember("listSize"))
	{
		if (item["listSize"].IsString())
		{
			m_listSize = item["listSize"].GetString();
		}
		else
		{
			throw new runtime_error("ListSize configuration item property is not a string");
		}
	}
	if (item.HasMember("listName"))
	{
		if (item["listName"].IsString())
		{
			m_listName = item["listName"].GetString();
		}
		else
		{
			throw new runtime_error("ListName configuration item property is not a string");
		}
	}

	std::string m_typeUpperCase = m_type;
	for (auto & c: m_typeUpperCase) c = toupper(c);

	// Item "value" can be an escaped JSON string, so check m_type JSON as well
	if (item.HasMember("value") &&
	    (item["value"].IsObject() || m_typeUpperCase.compare("JSON") == 0))

	{
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["value"].Accept(writer);
		m_value = item["value"].IsObject() ?
			  // use current string
			  strbuf.GetString() :
			  // Unescape the string
			  JSONunescape(strbuf.GetString());

		// If it's not a real eject, check the string buffer it is:
		if (!item["value"].IsObject())
		{
			Document check;
			check.Parse(m_value.c_str());
			if (check.HasParseError())
			{
				Logger::getLogger()->error("The JSON configuration item %s has a parse error: %s",
					m_name.c_str(), GetParseError_En(check.GetParseError()));
				throw new runtime_error(GetParseError_En(check.GetParseError()));
			}
			if (!check.IsObject())
			{
				Logger::getLogger()->error("The JSON configuration item %s is not a valid JSON objects",
						m_name.c_str());
				throw new runtime_error("'value' JSON property is not an object");
			}
		}
		if (m_typeUpperCase.compare("JSON") == 0)
		{
			m_itemType = JsonItem;
		}
		else
		{
			// Avoids overwrite if it is already valued
			if (m_itemType == StringItem)
			{
				m_itemType = JsonItem;
			}
		}
	}
	// Item "value" is a Bool or m_type is boolean
	else if (item.HasMember("value") &&
		 (item["value"].IsBool() || m_type.compare("boolean") == 0))
	{
		m_value = !item["value"].IsBool() ?
			  // use string value
			  item["value"].GetString() :
			  // use bool value
			  item["value"].GetBool() ? "true" : "false";	
		
		m_itemType = BoolItem;
	}
	// Item "value" is just a string
	else if (item.HasMember("value") && item["value"].IsString())
	{
		// Get content of script type item as is
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["value"].Accept(writer);

		if (m_itemType == ScriptItem ||
		    m_itemType == CodeItem)
		{
			m_value = strbuf.GetString();
			if (m_value.empty())
			{
				m_value = "\"\"";
			}
		}
		else
		{
			m_value = JSONunescape(strbuf.GetString());

			if (m_options.size() == 0)
				m_itemType = StringItem;
			else
				m_itemType = EnumerationItem;
		}
	}
	// Item "value" is a Double
	else if (item.HasMember("value") && item["value"].IsDouble())
	{
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["value"].Accept(writer);
		m_value = strbuf.GetString();
		m_itemType = DoubleItem;
	}
	// Item "value" is a Number
	else if (item.HasMember("value") && item["value"].IsNumber())
	{
		// Don't check Uint/Int/Long etc: just get the string value
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["value"].Accept(writer);
		m_value = strbuf.GetString();
		m_itemType = NumberItem;
	}
	// Item "value" has an unknwon type so far: set empty string
	else
	{
		m_value = "";
	}

	// Item "default" can be an escaped JSON string, so check m_type JSON as well
	if (item.HasMember("default") &&
	    (item["default"].IsObject() || m_typeUpperCase.compare("JSON") == 0))
	{
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["default"].Accept(writer);
		m_default = item["default"].IsObject() ?
			  // use current string
			  strbuf.GetString() :
			  // Unescape the string
			  JSONunescape(strbuf.GetString());

		// If it's not a real eject, check the string buffer it is:
		if (!item["default"].IsObject())
		{
			Document check;
			check.Parse(m_default.c_str());
			if (check.HasParseError())
			{
				Logger::getLogger()->error("The JSON configuration item %s has a parse error in the default value: %s",
					m_name.c_str(), GetParseError_En(check.GetParseError()));
				throw new runtime_error(GetParseError_En(check.GetParseError()));
			}
			if (!check.IsObject())
			{
				Logger::getLogger()->error("The JSON configuration item %s default is not a valid JSON object",
						m_name.c_str());
				throw new runtime_error("'default' JSON property is not an object");
			}
		}
		if (m_typeUpperCase.compare("JSON") == 0)
		{

			m_itemType = JsonItem;
		}
		else
		{
			// Avoids overwrite if it is already valued
			if (m_itemType == StringItem)
			{
				m_itemType = JsonItem;
			}
		}
	}
	// Item "default" is a Bool or m_type is boolean
	else if (item.HasMember("default") &&
		 (item["default"].IsBool() || m_type.compare("boolean") == 0))
	{
		m_default = !item["default"].IsBool() ?
			    // use string value
			    item["default"].GetString() :
			    // use bool value
			    item["default"].GetBool() ? "true" : "false";	
		
		m_itemType = BoolItem;
	}
	// Item "default" is just a string
	else if (item.HasMember("default") && item["default"].IsString())
	{
		// Get content of script type item as is
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["default"].Accept(writer);
		if (m_itemType == ScriptItem ||
		    m_itemType == CodeItem)
		{
			m_default = strbuf.GetString();
			if (m_default.empty())
			{
				m_default = "\"\"";
			}
		}
		else
		{
			m_default = JSONunescape(strbuf.GetString());
			if (m_options.size() == 0)
				m_itemType = StringItem;
			else
				m_itemType = EnumerationItem;
		}
	}
	// Item "default" is a Double
	else if (item.HasMember("default") && item["default"].IsDouble())
	{
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["default"].Accept(writer);
		m_default = strbuf.GetString();
		m_itemType = DoubleItem;
	}
	// Item "default" is a Number
	else if (item.HasMember("default") && item["default"].IsNumber())
	{
		// Don't check Uint/Int/Long etc: just get the string value
		rapidjson::StringBuffer strbuf;
		rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
		item["default"].Accept(writer);
		m_default = strbuf.GetString();
		m_itemType = NumberItem;
	}
	else
	// Item "default" has an unknwon type so far: set empty string
	{
		m_default = "";
	}
}

/**
 * Constructor for a configuration item
 */
ConfigCategory::CategoryItem::CategoryItem(const string& name, const std::string& description,
                                           const std::string& type, const std::string def,
                                           const std::string& value)
{
	m_name = name;
	m_description = description;
	m_type = type;
	m_default = def;
	m_value = value;
	m_itemType = StringItem;
}

/**
 * Constructor for a configuration item
 */
ConfigCategory::CategoryItem::CategoryItem(const string& name, const std::string& description,
                                           const std::string def, const std::string& value,
					   const vector<string> options)
{
	m_name = name;
	m_description = description;
	m_type = "enumeration";
	m_default = def;
	m_value = value;
	m_itemType = StringItem;
	for (auto it = options.cbegin(); it != options.cend(); it++)
	{
		m_options.push_back(*it);
	}
}

/**
 * Copy constructor for configuration item
 */
ConfigCategory::CategoryItem::CategoryItem(const CategoryItem& rhs)
{
	m_name = rhs.m_name;
	m_displayName = rhs.m_displayName;
	m_type = rhs.m_type;
	m_default = rhs.m_default;
	m_value = rhs.m_value;
	m_description = rhs.m_description;
       	m_order = rhs.m_order;
       	m_readonly = rhs.m_readonly;
       	m_mandatory = rhs.m_mandatory;
       	m_deprecated = rhs.m_deprecated;
       	m_length = rhs.m_length;
       	m_minimum = rhs.m_minimum;
       	m_maximum = rhs.m_maximum;
       	m_filename = rhs.m_filename;
	for (auto it = rhs.m_options.cbegin(); it != rhs.m_options.cend(); it++)
	{
		m_options.push_back(*it);
	}
       	m_file = rhs.m_file;
       	m_itemType = rhs.m_itemType;
	m_validity = rhs.m_validity;
	m_group = rhs.m_group;
	m_rule = rhs.m_rule;
	m_bucketProperties = rhs.m_bucketProperties;
	m_listSize = rhs.m_listSize;
	m_listItemType = rhs.m_listItemType;
	m_listName = rhs.m_listName;
	for (auto it = rhs.m_permissions.cbegin(); it != rhs.m_permissions.cend(); it++)
	{
		m_permissions.push_back(*it);
	}
}

/**
 * Create a JSON representation of the configuration item
 *
 * @param full	false is the default, true evaluates all the members of the CategoryItem
 *
 */
string ConfigCategory::CategoryItem::toJSON(const bool full) const
{
ostringstream convert;

	convert << "\"" << JSONescape(m_name) << "\" : { ";
	convert << "\"description\" : \"" << JSONescape(m_description) << "\", ";
	if (! m_displayName.empty())
	{
		convert << "\"displayName\" : \"" << m_displayName << "\", ";
	}
	convert << "\"type\" : \"" << m_type << "\", ";
	if (m_options.size() > 0)
	{
		convert << "\"options\" : [ ";
		for (int i = 0; i < m_options.size(); i++)
		{
			if (i > 0)
				convert << ",";
			convert << "\"" << m_options[i] << "\"";
		}
		convert << "], ";
	}

	if (m_permissions.size() > 0)
	{
		convert << "\"permissions\" : [ ";
		for (int i = 0; i < m_permissions.size(); i++)
		{
			if (i > 0)
				convert << ",";
			convert << "\"" << m_permissions[i] << "\"";
		}
		convert << "], ";
	}

	if (m_itemType == StringItem ||
	    m_itemType == BoolItem ||
	    m_itemType == EnumerationItem ||
	    m_itemType == BucketItem ||
	    m_itemType == ListItem ||
	    m_itemType == KVListItem)
	{
		convert << "\"value\" : \"" << JSONescape(m_value) << "\", ";
		convert << "\"default\" : \"" << JSONescape(m_default) << "\"";
	}
	else if (m_itemType == JsonItem ||
		 m_itemType == NumberItem ||
		 m_itemType == DoubleItem ||
		 m_itemType == ScriptItem ||
		 m_itemType == CodeItem)
	{
		convert << "\"value\" : " << m_value << ", ";
		convert << "\"default\" : " << m_default;
	}
	else
	{
		Logger::getLogger()->error("Unknown item type in configuration category");
	}

	if (full)
	{
		if (!m_order.empty())
		{
			convert << ", \"order\" : \"" << m_order << "\"";
		}

	        if (!m_length.empty())
		{
			convert << ", \"length\" : \"" << m_length << "\"";
		}

		if (!m_minimum.empty())
		{
			convert << ", \"minimum\" : \"" << m_minimum << "\"";
		}

		if (!m_maximum.empty())
		{
			convert << ", \"maximum\" : \"" << m_maximum << "\"";
		}

		if (!m_readonly.empty())
		{
			convert << ", \"readonly\" : \"" << m_readonly << "\"";
		}

		if (!m_mandatory.empty())
		{
			convert << ", \"mandatory\" : \"" << m_mandatory << "\"";
		}

		if (!m_validity.empty())
		{
			convert << ", \"validity\" : \"" << JSONescape(m_validity) << "\"";
		}

		if (!m_rule.empty())
		{
			convert << ", \"rule\" : \"" << JSONescape(m_rule) << "\"";
		}

		if (!m_bucketProperties.empty())
		{
			convert << ", \"properties\" : " << m_bucketProperties;
		}

		if (!m_group.empty())
		{
			convert << ", \"group\" : \"" << m_group << "\"";
		}

		if (!m_file.empty())
		{
			convert << ", \"file\" : \"" << m_file << "\"";
		}

		if (!m_listSize.empty())
		{
			convert << ", \"listSize\" : \"" << m_listSize << "\"";
		}
		if (!m_listItemType.empty())
		{
			convert << ", \"items\" : \"" << m_listItemType << "\"";
		}
		if (!m_listName.empty())
		{
			convert << ", \"listName\" : \"" << m_listName << "\"";
		}
	}
	convert << " }";

	return convert.str();
}

/**
 * Return only "default" item values
 */
string ConfigCategory::CategoryItem::defaultToJSON() const
{
ostringstream convert;

	convert << "\"" << JSONescape(m_name) << "\" : { ";
	convert << "\"description\" : \"" << JSONescape(m_description) << "\", ";
	convert << "\"type\" : \"" << m_type << "\"";

	if (!m_order.empty())
	{
		convert << ", \"order\" : \"" << m_order << "\"";
	}

	if (!m_displayName.empty())
	{
		convert << ", \"displayName\" : \"" << m_displayName << "\"";
	}

	if (!m_length.empty())
	{
		convert << ", \"length\" : \"" << m_length << "\"";
	}

	if (!m_minimum.empty())
	{
		convert << ", \"minimum\" : \"" << m_minimum << "\"";
	}

	if (!m_maximum.empty())
	{
		convert << ", \"maximum\" : \"" << m_maximum << "\"";
	}

	if (!m_readonly.empty())
	{
		convert << ", \"readonly\" : \"" << m_readonly << "\"";
	}

	if (!m_mandatory.empty())
	{
		convert << ", \"mandatory\" : \"" << m_mandatory << "\"";
	}

	if (!m_validity.empty())
	{
		convert << ", \"validity\" : \"" << JSONescape(m_validity) << "\"";
	}

	if (!m_rule.empty())
	{
		convert << ", \"rule\" : \"" << JSONescape(m_rule) << "\"";
	}

	if (!m_bucketProperties.empty())
	{
		convert << ", \"properties\" : " << m_bucketProperties;
	}

	if (!m_group.empty())
	{
		convert << ", \"group\" : \"" << m_group << "\"";
	}

	if (!m_file.empty())
	{
		convert << ", \"file\" : \"" << m_file << "\"";
	}
	if (m_options.size() > 0)
	{
		convert << ", \"options\" : [ ";
		for (int i = 0; i < m_options.size(); i++)
		{
			if (i > 0)
				convert << ",";
			convert << "\"" << m_options[i] << "\"";
		}
		convert << "]";
	}
	if (m_permissions.size() > 0)
	{
		convert << ", \"permissions\" : [ ";
		for (int i = 0; i < m_permissions.size(); i++)
		{
			if (i > 0)
				convert << ",";
			convert << "\"" << m_permissions[i] << "\"";
		}
		convert << "]";
	}
	if (!m_listSize.empty())
	{
		convert << ", \"listSize\" : \"" << m_listSize << "\"";
	}
	if (!m_listItemType.empty())
	{
		convert << ", \"items\" : \"" << m_listItemType << "\"";
	}
	if (!m_listName.empty())
	{
	    convert << ", \"listName\" : \"" << m_listName << "\"";
	}


	if (m_itemType == StringItem ||
	    m_itemType == EnumerationItem ||
	    m_itemType == BoolItem ||
	    m_itemType == BucketItem ||
	    m_itemType == ListItem ||
	    m_itemType == KVListItem)
	{
		convert << ", \"default\" : \"" << JSONescape(m_default) << "\" }";
	}
	/**
	 * NOTE:
	 * These data types must be all escaped.
	 * "default" items in the DefaultConfigCategory class are sent to
	 * ConfigurationManager interface which requires string values only:
	 *
	 * examples:
	 * we must use "100" not 100
	 * and for JSON
	 * "{\"pipeline\":[\"scale\"]}" not {"pipeline":["scale"]}
	 */
	else if (m_itemType == JsonItem ||
		 m_itemType == NumberItem ||
		 m_itemType == DoubleItem ||
		 m_itemType == ScriptItem ||
		 m_itemType == CodeItem)
	{
		convert << ", \"default\" : \"" << JSONescape(m_default) << "\" }";
	}
	return convert.str();
}

/**
 * Parse BucketItem value in JSON dict format and return the key value pairs within that
 *
 * @param json	JSON string representing the BucketItem value
 * @return		Vector with pairs of found key/value string pairs in BucketItem value
 */
vector<pair<string,string>>* ConfigCategory::parseBucketItemValue(const string & json)
{
	Document document;
	if (document.Parse(json.c_str()).HasParseError())
	{
		Logger::getLogger()->error("parseBucketItemValue(): The provided JSON string has a parse error: %s",
				GetParseError_En(document.GetParseError()));
		return NULL;
	}
	
	vector<pair<string,string>> *vec = new vector<pair<string,string>>;
	
	for (const auto & m : document.GetObject())
		vec->emplace_back(make_pair<string,string>(m.name.GetString(), m.value.GetString()));

	return vec;
}


// DefaultConfigCategory constructor
DefaultConfigCategory::DefaultConfigCategory(const string& name, const string& json) :
                                            ConfigCategory::ConfigCategory(name, json)
{
}

/**
 * Destructor for the default configuration category. Simply call the base class
 * destructor.
 */
DefaultConfigCategory::~DefaultConfigCategory()
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
	convert << "\"key\" : \"" << JSONescape(m_name) << "\", ";
	convert << "\"description\" : \"" << JSONescape(m_description) << "\", \"value\" : ";
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
        
	convert << "{";
	for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
	{       
		convert << (*it)->defaultToJSON();
		if (it + 1 != m_items.cend() )
		{       
			convert << ", ";
		}
	}
	convert << "}";

	return convert.str();
}

/**
 * Return JSON string of a category item
 * @param itemName	The given item within current category
 * @return		The JSON string version of itemName
 *			If not found {} is returned
 */
string ConfigCategory::itemToJSON(const string& itemName) const
{
	ostringstream convert;
        
        convert << "{";
        for (auto it = m_items.cbegin(); it != m_items.cend(); it++)
        {
		if ((*it)->m_name.compare(itemName) == 0)
		{
                	convert << (*it)->toJSON();
		}
	}
	convert << "}";
        
	return convert.str();
}

/**
 * Configuration Category constructor
 *
 * @param name	The name of the configuration category
 * @param json	JSON content of the configuration category
 */
ConfigCategoryChange::ConfigCategoryChange(const string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("Configuration parse error in category change %s: %s at %d",
			json.c_str(), GetParseError_En(doc.GetParseError()),
			(unsigned)doc.GetErrorOffset());
		throw new ConfigMalformed();
	}
	if (!doc.HasMember("category"))
	{
		Logger::getLogger()->error("Configuration change is missing a category element '%s'",
			json.c_str());
		throw new ConfigMalformed();
	}

	if (doc.HasMember("parent_category"))
	{
		m_parent_name=doc["parent_category"].GetString();
	} else {
		m_parent_name="";
	}

	if (!doc.HasMember("items"))
	{
		Logger::getLogger()->error("Configuration change is missing an items element '%s'",
			json.c_str());
		throw new ConfigMalformed();
	}

	m_name = doc["category"].GetString();
	const Value& items = doc["items"];
	for (Value::ConstMemberIterator itr = items.MemberBegin(); itr != items.MemberEnd(); ++itr)
	{
		try
		{
			m_items.push_back(new CategoryItem(itr->name.GetString(), itr->value));
		}
		catch (exception* e)
		{
			Logger::getLogger()->error("Configuration parse error in category %s item '%s', %s: %s",
				m_name.c_str(),
				itr->name.GetString(),
				json.c_str(),
				e->what());
			delete e;
			throw ConfigMalformed();
		}
		catch (...)
		{
			throw;
		}
	}
}
