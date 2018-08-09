#ifndef _CONFIG_CATEGORY_H
#define _CONFIG_CATEGORY_H

/*
 * FogLAMP category management
 *
 * Copyright (c) 2017-2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */

#include <string>
#include <vector>
#include <rapidjson/document.h>

class ConfigCategoryDescription {
	public:
		ConfigCategoryDescription(const std::string& name, const std::string& description) :
				m_name(name), m_description(description) {};
		std::string	getName() const { return m_name; };
		std::string	getDescription() const { return m_description; };
		// JSON string with m_name and m_description
		std::string 	toJSON() const;
	private:
		const std::string	m_name;
		const std::string	m_description;
};

class ConfigCategories {
	public:
		ConfigCategories(const std::string& json); 
		ConfigCategories(); // Constructor without parameters
		~ConfigCategories();
		unsigned int			length() { return m_categories.size(); };
		ConfigCategoryDescription 	*operator[] (const unsigned int idx) {
						return m_categories[idx];
					};
		// Add one category name with description
		void			addCategoryDescription(ConfigCategoryDescription* elem);
		// JSON string of all categories
		std::string		toJSON() const;

	private:
		std::vector<ConfigCategoryDescription *> 	m_categories;
	
};

class ConfigCategory {
	public:
		ConfigCategory(const std::string& name, const std::string& json);
		ConfigCategory() {};
		ConfigCategory(const ConfigCategory& orig);
		~ConfigCategory();
		void				addItem(const std::string& name, const std::string description,
							const std::string& type, const std::string def,
							const std::string& value);
		void				setDescription(const std::string& description);
		std::string                     getName() const { return m_name; };
		std::string                     getDescription() const { return m_description; };
		unsigned int			getCount() const { return m_items.size(); };
		bool				itemExists(const std::string& name) const;
		std::string			getValue(const std::string& name) const;
		std::string			getType(const std::string& name) const;
		std::string			getDescription(const std::string& name) const;
		std::string			getDefault(const std::string& name) const;
		bool				isString(const std::string& name) const;
		bool				isJSON(const std::string& name) const;
		bool				isBool(const std::string& name) const;
		bool				isNumber(const std::string& name) const;
		bool				isDouble(const std::string& name) const;
		std::string			toJSON() const;
		std::string			itemsToJSON() const;
		ConfigCategory& 		operator=(ConfigCategory const& rhs);
		void				setItemsValueFromDefault();
		void				checkDefaultValuesOnly() const;
		std::string 			itemToJSON(const std::string& itemName) const;

	protected:
		class CategoryItem {
			public:
				enum ItemType { StringItem, JsonItem, BoolItem, NumberItem, DoubleItem };
				CategoryItem(const std::string& name, const rapidjson::Value& item);
				CategoryItem(const std::string& name, const std::string& description,
							const std::string& type, const std::string def,
							const std::string& value);
				// Return both "value" and "default" items
				std::string	toJSON() const;
				// Return only "default" items
				std::string	defaultToJSON() const;
				std::string	escape(const std::string& str) const;
				std::string	unescape(const std::string& subject) const;

			public:
				std::string 	m_name;
				std::string 	m_type;
				std::string 	m_default;
				std::string 	m_value;
				std::string 	m_description;
				ItemType	m_itemType;
		};
		std::vector<CategoryItem *>	m_items;
		std::string			m_name;
		std::string			m_description;
};

/**
 * DefaultConfigCategory
 *
 * json input parameter must contain only "default" items.
 * itemsToJSON() reports only "defaults"
 *
 * This class must be used when creating/updating a category
 * via ManagementClient::addCategoryDefault(DefaultConfigCategory categoryDefault)
 */

class DefaultConfigCategory : public ConfigCategory
{
	public:
		DefaultConfigCategory(const std::string& name, const std::string& json);
		DefaultConfigCategory(const ConfigCategory& orig) : ConfigCategory(orig)
		{
		};
	
		std::string	toJSON() const;
		std::string	itemsToJSON() const;
};

class ConfigItemNotFound : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "Configuration item not found in configuration category";
		}
};

class ConfigMalformed : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "Configuration category JSON is malformed";
		}
};

/**
 * This exception must be raised when at least one of the JSON items of a
 * new being created category have both "value" and "default" fields.
 */
class ConfigValueFoundWithDefault : public std::exception {
	public:
		// Constructor with parameter
		ConfigValueFoundWithDefault(const std::string& item)
		{
			m_errmsg = "Configuration item '";
			m_errmsg.append(item);
			m_errmsg += "' has both 'value' and 'default' fields.";
		};

		virtual const char *what() const throw()
		{
			return m_errmsg.c_str();
		}
	private:
		std::string	m_errmsg;
};
#endif
