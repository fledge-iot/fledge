#ifndef _CONFIG_CATEGORY_H
#define _CONFIG_CATEGORY_H

/*
 * Fledge category management
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
#include <json_utils.h>

class ConfigCategoryDescription {
	public:
		ConfigCategoryDescription(const std::string& name, const std::string& description) :
				m_name(name), m_displayName(name), m_description(description) {};
		ConfigCategoryDescription(const std::string& name, const std::string& displayName, const std::string& description) :
				m_name(name), m_displayName(displayName), m_description(description) {};
		std::string	getName() const { return m_name; };
		std::string	getDisplayName() const { return m_displayName; };
		std::string	getDescription() const { return m_description; };
		// JSON string with m_name and m_description
		std::string 	toJSON() const;
	private:
		const std::string	m_name;
		const std::string	m_displayName;
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
		enum ItemType {
			UnknownType,
			StringItem,
			EnumerationItem,
			JsonItem,
			BoolItem,
			NumberItem,
			DoubleItem,
			ScriptItem,
			CategoryType,
			CodeItem
		};

		ConfigCategory(const std::string& name, const std::string& json);
		ConfigCategory() {};
		ConfigCategory(const ConfigCategory& orig);
		~ConfigCategory();
		void				addItem(const std::string& name, const std::string description,
							const std::string& type, const std::string def,
							const std::string& value);
		void				addItem(const std::string& name, const std::string description,
							const std::string def, const std::string& value,
							const std::vector<std::string> options);
    		void 				removeItems();
		void 				removeItemsType(ItemType type);
		void 				keepItemsType(ItemType type);
		bool                            extractSubcategory(ConfigCategory &subCategories);
		void				setDescription(const std::string& description);
		std::string                     getName() const { return m_name; };
		std::string                     getDescription() const { return m_description; };

		std::string                     getDisplayName() const { return m_displayName; };
		void                            setDisplayName(const std::string& displayName) {m_displayName = displayName;};

		unsigned int			getCount() const { return m_items.size(); };
		bool				itemExists(const std::string& name) const;
		bool				setItemDisplayName(const std::string& name, const std::string& displayName);
		std::string			getValue(const std::string& name) const;
		std::string			getType(const std::string& name) const;
		std::string			getDescription(const std::string& name) const;
		std::string			getDefault(const std::string& name) const;
		bool				setDefault(const std::string& name, const std::string& value);
		bool				setValue(const std::string& name, const std::string& value);
		std::string			getDisplayName(const std::string& name) const;
		std::vector<std::string>	getOptions(const std::string& name) const;
		std::string			getLength(const std::string& name) const;
		std::string			getMinimum(const std::string& name) const;
		std::string			getMaximum(const std::string& name) const;
		bool				isString(const std::string& name) const;
		bool				isEnumeration(const std::string& name) const;
		bool				isJSON(const std::string& name) const;
		bool				isBool(const std::string& name) const;
		bool				isNumber(const std::string& name) const;
		bool				isDouble(const std::string& name) const;
		bool				isDeprecated(const std::string& name) const;
		std::string			toJSON(const bool full=false) const;
		std::string			itemsToJSON(const bool full=false) const;
		ConfigCategory& 		operator=(ConfigCategory const& rhs);
		ConfigCategory& 		operator+=(ConfigCategory const& rhs);
		void				setItemsValueFromDefault();
		void				checkDefaultValuesOnly() const;
		std::string 			itemToJSON(const std::string& itemName) const;
		enum ItemAttribute {
					ORDER_ATTR,
					READONLY_ATTR,
					MANDATORY_ATTR,
					FILE_ATTR};
		std::string			getItemAttribute(const std::string& itemName,
								 ItemAttribute itemAttribute) const;

	protected:
		class CategoryItem {
			public:
				CategoryItem(const std::string& name, const rapidjson::Value& item);
				CategoryItem(const std::string& name, const std::string& description,
					     const std::string& type, const std::string def,
					     const std::string& value);
				CategoryItem(const std::string& name, const std::string& description,
					     const std::string def, const std::string& value,
					     const std::vector<std::string> options);
				CategoryItem(const CategoryItem& rhs);
				// Return both "value" and "default" items
				std::string	toJSON(const bool full=false) const;
				// Return only "default" items
				std::string	defaultToJSON() const;

			public:
				std::string 	m_name;
				std::string	m_displayName;
				std::string 	m_type;
				std::string 	m_default;
				std::string 	m_value;
				std::string 	m_description;
				std::string 	m_order;
				std::string 	m_readonly;
				std::string 	m_mandatory;
				std::string 	m_deprecated;
				std::string	m_length;
				std::string	m_minimum;
				std::string	m_maximum;
				std::string 	m_filename;
				std::vector<std::string>
						m_options;
				std::string 	m_file;
				ItemType	m_itemType;
		};
		std::vector<CategoryItem *>	m_items;
		std::string			m_name;
		std::string			m_description;
		std::string			m_displayName;

	public:
		using iterator = std::vector<CategoryItem *>::iterator;
  		using const_iterator = std::vector<CategoryItem *>::const_iterator;

		const_iterator begin() const { return m_items.begin(); }
		const_iterator end() const { return m_items.end(); }
		const_iterator cbegin() const { return m_items.cbegin(); }
		const_iterator cend() const { return m_items.cend(); }
		
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
		~DefaultConfigCategory();
		std::string	toJSON() const;
		std::string	itemsToJSON() const;
};

class ConfigCategoryChange : public ConfigCategory
{
	public:
		ConfigCategoryChange(const std::string& json);
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

/**
 * This exception must be raised when a requested item attribute
 * does not exist.
 * Supported item attributes: "order", "readonly", "file".
 */
class ConfigItemAttributeNotFound : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "Configuration item attribute not found in configuration category";
		}
};
#endif
