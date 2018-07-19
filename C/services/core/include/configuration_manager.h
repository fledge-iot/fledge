#ifndef _CONFIGURATION_MANAGER_H
#define _CONFIGURATION_MANAGER_H

/*
 * FogLAMP Configuration management.
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
		// Called by GET /foglamp/service/category
		ConfigCategories		getAllCategoryNames() const;
		// Called by GET /foglamp/service/category/{category_name}
		ConfigCategory			getCategoryAllItems(const std::string& categoryName) const;
		// Called by POST /foglamp/service/category
		ConfigCategory			createCategory(const std::string& categoryName,
							       const std::string& categoryDescription,
							       const std::string& categoryItems) const;
		// Called by GET /foglamp/category/{categoryName}/{configItem}
		std::string			getCategoryItem(const std::string& categoryName,
								const std::string& itemName) const;
		// Called by PUT /foglamp/category/{categoryName}/{configItem}
		bool				setCategoryItemValue(const std::string&categoryName,
								     const std::string& itemName,
								     const std::string& newValue) const;
		// Internal usage
		std::string			getCategoryItemValue(const std::string& categoryName,
								     const std::string& itemName) const;
	private:
		ConfigurationManager(const std::string& host,
				     unsigned short port);
		~ConfigurationManager();
		void mergeCategoryValues(rapidjson::Value& inputValues,
					 const rapidjson::Value* storedValues,
					 rapidjson::Document::AllocatorType& allocator) const;
	private:
		static  ConfigurationManager*	m_instance;
		StorageClient*			m_storage;
};

/**
 * NoSuchCategoryException
 */
class NoSuchCategoryException : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Config category does not exist";
		}
};

/**
 * NoSuchItemException
 */
class NoSuchItemException : public std::exception {
	public:
		NoSuchItemException(const std::string& message)
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
 * CategoryDetailsException
 */
class CategoryDetailsException : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Cannot access row informations";
		}
};

/**
 * StorageOperationException
 */
class StorageOperationException : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Failure while performing insert or update operation";
		}
};
/**
 * NotSupportedDataTypeException
 */
class NotSupportedDataTypeException : public std::exception {
	public:
		virtual const char* what() const throw()
		{
			return "Data type not supported";
		}
};
#endif
