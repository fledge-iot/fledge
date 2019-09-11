#ifndef _CONFIGURATION_MANAGER_H
#define _CONFIGURATION_MANAGER_H

/*
 * Fledge Configuration management.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <storage_client.h>
#include <config_category.h>
#include <string>

class ConfigurationManager {
        public:
		static ConfigurationManager*	getInstance(const std::string&, short unsigned int);
		// Called by microservice management API or the admin API:
		// GET /fledge/service/category
		// GET /fledge//category
		ConfigCategories		getAllCategoryNames() const;
		// Called by microservice management API or the admin API:
		// GET /fledge/service/category/{category_name}
		// GET /fledge/category/{category_name}
		ConfigCategory			getCategoryAllItems(const std::string& categoryName) const;
		// Called by microservice management API or the admin API:
		// POST /fledge/service/category
		// POST /fledge/category
		ConfigCategory			createCategory(const std::string& categoryName,
							       const std::string& categoryDescription,
							       const std::string& categoryItems,
							       bool keepOriginalIterms = false) const;
		// Called by microservice management API or the admin API:
		// GET /fledge/service/category/{categoryName}/{configItem}
		// GET /fledge/category/{categoryName}/{configItem}
		std::string			getCategoryItem(const std::string& categoryName,
								const std::string& itemName) const;
		// Called by microservice management API or the admin API:
		// PUT /fledge/service/category/{categoryName}/{configItem}
		// PUT /fledge/service/{categoryName}/{configItem}
		bool				setCategoryItemValue(const std::string& categoryName,
								     const std::string& itemName,
								     const std::string& newValue) const;
		// Called by microservice management API or the admin API:
		// POST /fledge/service/category/{categoryName}/children
		// POST /fledge/category/{categoryName}/children
		std::string			addChildCategory(const std::string& parentCategoryName,
								 const std::string& childCategories) const;
		// Called by microservice management API or the admin API:
		// GET /fledge/service/category/{categoryName}/children
		// GET /fledge/category/{categoryName}/children
		ConfigCategories		getChildCategories(const std::string& parentCategoryName) const;
		// Called by microservice management API or the admin API:
		// DELETE /fledge/service/category/{CategoryName}/children/{ChildCategory}
		// DELETE /fledge/category/{CategoryName}/children/{ChildCategory}
		std::string			deleteChildCategory(const std::string& parentCategoryName,
								    const std::string& childCategory) const;
		// Called by microservice management API or the admin API:
		// DELETE /fledge/service/category/{categoryName}/{configItem}/value
		// DELETE /fledge/category/{categoryName}/{configItem}/value
		std::string 			deleteCategoryItemValue(const std::string& categoryName,
									const std::string& itemName) const;
		// Called by microservice management API or the admin API:
		// DELETE /fledge/service/category/{categoryName}
		// DELETE /fledge/category/{categoryName}
		ConfigCategories		deleteCategory(const std::string& categoryName) const;
		// Internal usage
		std::string			getCategoryItemValue(const std::string& categoryName,
								     const std::string& itemName) const;

	private:
		ConfigurationManager(const std::string& host,
				     unsigned short port);
		~ConfigurationManager();
		void		mergeCategoryValues(rapidjson::Value& inputValues,
						    const rapidjson::Value* storedValues,
						    rapidjson::Document::AllocatorType& allocator,
						    bool keepOriginalitems) const;
		// Internal usage
		std::string	fetchChildCategories(const std::string& parentCategoryName) const;
		std::string	getCategoryDescription(const std::string& categoryName) const;

	private:
		static  ConfigurationManager*	m_instance;
		StorageClient*			m_storage;
};

/**
 * NoSuchCategory
 */
class NoSuchCategory : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Config category does not exist";
		}
};

/**
 * NoSuchCategoryItemValue
 */
class NoSuchCategoryItemValue : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Failure while fetching config category item value";
		}
};

/**
 * NoSuchItem
 */
class NoSuchCategoryItem : public std::exception {
	public:
		NoSuchCategoryItem(const std::string& message)
		{
			m_error = message;
		}
				
		virtual const char* what() const throw()
		{
			return m_error.c_str();
		}

	private:
		std::string m_error;
};

/**
 * CategoryDetailsEx
 */
class CategoryDetailsEx : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Cannot access category informations";
		}
};

/**
 * StorageOperation
 */
class StorageOperation : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Failure while performing insert or update operation";
		}
};

/**
 * NotSupportedDataType
 */
class NotSupportedDataType : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Data type not supported";
		}
};

/**
 * AllCategoriesEx
 */
class AllCategoriesEx : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Failure while fetching all config categories";
		}
};

/**
 * ConfigCategoryDefaultWithValue
 */
class ConfigCategoryDefaultWithValue : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "The config category being inserted/updated has both default and value properties for items";
		}
};

/**
 * ConfigCategoryEx
 */
class ConfigCategoryEx : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Failure while setting/fetching a config category";
		}
};

/**
 * ChildCategoriesEx
 */
class ChildCategoriesEx : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Failure while setting/fetching child categories";
		}
};

/**
 * ExistingChildCategories
 */
class ExistingChildCategories : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Requested child categories are already set for the given parent category";
		}
};
#endif
