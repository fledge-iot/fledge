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
#include "rapidjson/error/error.h"
#include "rapidjson/error/en.h"
#include <sstream>
#include <iostream>
#include <time.h>
#include <stdlib.h>
#include <logger.h>

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
 * the FogLAMP configuratrion service.
 */
ConfigCategories::ConfigCategories(const std::string& json)
{
	Document doc;
	doc.Parse(json.c_str());
	if (doc.HasParseError())
	{
		Logger::getLogger()->error("Configuration parse error in %s: %s at %d", json.c_str(),
			GetParseError_En(doc.GetParseError()), (unsigned)doc.GetErrorOffset());
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

	convert << "{\"key\": \"" << m_name << "\", ";
	convert << "\"description\" : \"" << m_description << "\"}";

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
		Logger::getLogger()->error("Configuration parse error in category '%s', %s: %s at %d",
			name.c_str(), json.c_str(),
			GetParseError_En(doc.GetParseError()), (unsigned)doc.GetErrorOffset());
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
				case FILE_ATTR:
					return m_items[i]->m_file;
				default:
					throw new ConfigItemAttributeNotFound();
			}
		}
	}
	throw new ConfigItemNotFound();
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

	convert << "{ \"key\" : \"" << m_name << "\", ";
	convert << "\"description\" : \"" << m_description << "\", \"value\" : ";
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
	if  (m_type.compare("category") == 0)
	{

		m_itemType = CategoryType;
	}
	if  (m_type.compare("script") == 0)
	{

		m_itemType = ScriptItem;
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

	std:string m_typeUpperCase = m_type;
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
			  this->unescape(strbuf.GetString());

		// If it's not a real eject, check the string buffer it is:
		if (!item["value"].IsObject())
		{
			Document check;
			check.Parse(m_value.c_str());
			if (check.HasParseError())
			{
				throw new runtime_error(GetParseError_En(check.GetParseError()));
			}
			if (!check.IsObject())
			{
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
		if (m_itemType == ScriptItem)
		{
			// Get content of script type item as is
			rapidjson::StringBuffer strbuf;
			rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
			item["value"].Accept(writer);
			m_value = strbuf.GetString();
			if (m_value.empty())
			{
				m_value = "\"\"";
			}
		}
		else
		{
			m_value = item["value"].GetString();
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
			  this->unescape(strbuf.GetString());

		// If it's not a real eject, check the string buffer it is:
		if (!item["default"].IsObject())
		{
			Document check;
			check.Parse(m_default.c_str());
			if (check.HasParseError())
			{
				throw new runtime_error(GetParseError_En(check.GetParseError()));
			}
			if (!check.IsObject())
			{
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
		if (m_itemType == ScriptItem)
		{
			// Get content of script type item as is
			rapidjson::StringBuffer strbuf;
			rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
			item["default"].Accept(writer);
			if (m_default.empty())
			{
				m_default = "\"\"";
			}
		}
		else
		{
			m_default = item["default"].GetString();
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
       	m_deprecated = rhs.m_deprecated;
       	m_minimum = rhs.m_minimum;
       	m_maximum = rhs.m_maximum;
       	m_filename = rhs.m_filename;
	for (auto it = rhs.m_options.cbegin(); it != rhs.m_options.cend(); it++)
	{
		m_options.push_back(*it);
	}
       	m_file = rhs.m_file;
       	m_itemType = rhs.m_itemType;
}

/**
 * Create a JSON representation of the configuration item
 *
 * @param full	false is the deafult, true evaluates all the members of the CategoryItem
 *
 */
string ConfigCategory::CategoryItem::toJSON(const bool full) const
{
ostringstream convert;

	convert << "\"" << m_name << "\" : { ";
	convert << "\"description\" : \"" << m_description << "\", ";
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

	if (m_itemType == StringItem ||
	    m_itemType == BoolItem ||
	    m_itemType == EnumerationItem)
	{
		convert << "\"value\" : \"" << m_value << "\", ";
		convert << "\"default\" : \"" << m_default << "\"";
	}
	else if (m_itemType == JsonItem ||
		 m_itemType == NumberItem ||
		 m_itemType == DoubleItem ||
		 m_itemType == ScriptItem)
	{
		convert << "\"value\" : " << m_value << ", ";
		convert << "\"default\" : " << m_default;
	}

	if (full)
	{
		if (!m_order.empty())
		{
			convert << ", \"order\" : \"" << m_order << "\"";
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

	convert << "\"" << m_name << "\" : { ";
	convert << "\"description\" : \"" << m_description << "\", ";
	convert << "\"type\" : \"" << m_type << "\"";

	if (!m_order.empty())
	{
		convert << ", \"order\" : \"" << m_order << "\"";
	}

	if (!m_displayName.empty())
	{
		convert << ", \"displayName\" : \"" << m_displayName << "\"";
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

	if (m_itemType == StringItem ||
	    m_itemType == EnumerationItem ||
	    m_itemType == BoolItem)
	{
		convert << ", \"default\" : \"" << m_default << "\" }";
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
		 m_itemType == ScriptItem)
	{
		convert << ", \"default\" : \"" << escape(m_default) << "\" }";
	}
	return convert.str();
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

std::string ConfigCategory::CategoryItem::escape(const std::string& subject) const
{
size_t pos = 0;
string replace("\\\"");
string escaped = subject;

	while ((pos = escaped.find("\"", pos)) != std::string::npos)
	{
		escaped.replace(pos, 1, replace);
		pos += replace.length();
	}
	return escaped;
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
 * Return unescaped version of a JSON string
 *
 * Routine removes \" inside the string
 * and leading and trailing "
 *
 * @param subject	Input string
 * @return		Unescaped string
 */
std::string ConfigCategory::CategoryItem::unescape(const std::string& subject) const
{
	size_t pos = 0;
	string replace("");
	string json = subject;

	// Replace '\"' with '"'
        while ((pos = json.find("\\\"", pos)) != std::string::npos)
        {
                json.replace(pos, 1, "");
        }
	// Remove leading '"'
	if (json[0] == '\"')
	{
		json.erase(0, 1);
	}
	// Remove trainling '"'
	if (json[json.length() - 1] == '\"')
	{
		json.erase(json.length() - 1, 1);
	}
        return json;
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
				m_name,
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
