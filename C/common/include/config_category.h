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
	private:
		const std::string	m_name;
		const std::string	m_description;
};

class ConfigCategories {
	public:
		ConfigCategories(const std::string& json);
		~ConfigCategories();
		unsigned int			length() { return m_categories.size(); };
		ConfigCategoryDescription 	*operator[] (const unsigned int idx) {
						return m_categories[idx];
					};
	private:
		std::vector<ConfigCategoryDescription *> 	m_categories;
	
};

class ConfigCategory {
	public:
		ConfigCategory(const std::string& name, const std::string& json);
		ConfigCategory() {};
		ConfigCategory(const ConfigCategory& orig);
		~ConfigCategory();
		void				setDescription(const std::string& description);
		unsigned int			getCount() const { return m_items.size(); };
		bool				itemExists(const std::string& name) const;
		std::string			getValue(const std::string& name) const;
		std::string			getType(const std::string& name) const;
		std::string			getDescription(const std::string& name) const;
		std::string			getDefault(const std::string& name) const;
		bool				isString(const std::string& name) const;
		bool				isJSON(const std::string& name) const;
		std::string			toJSON() const;
		std::string			itemsToJSON() const;
		ConfigCategory& 		operator=(ConfigCategory const& rhs);

	protected:
		class CategoryItem {
			public:
				enum ItemType { StringItem, JsonItem };
				CategoryItem(const std::string& name, const rapidjson::Value& item);
				// Return both "value" and "default" items
				std::string	toJSON() const;
				// Return only "default" items
				std::string	defaultToJSON() const;
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

	std::string	toJSON() const;
	std::string	itemsToJSON() const;
};

#endif
