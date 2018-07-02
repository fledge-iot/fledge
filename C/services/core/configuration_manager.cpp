/*
 * FogLAMP FogLAMP Configuration management.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <configuration_manager.h>
#include <rapidjson/writer.h>

using namespace std;
using namespace rapidjson;

ConfigurationManager *ConfigurationManager::m_instance = 0;

/**
 * Constructor
 *
 * @param host    Storage layer TCP address
 * @param port	  Storage layer TCP port
 */
ConfigurationManager::ConfigurationManager(const string& host,
					   unsigned short port)
{
	m_storage = new StorageClient(host, port);
}

// Destructor
ConfigurationManager::~ConfigurationManager()
{
	delete m_storage;
}

/**
 * Return the singleton instance of the configuration manager
 *
 * @param host    Storage layer TCP address
 * @param port	  Storage layer TCP port
 * @return        The configuration manager class instance
 */
ConfigurationManager* ConfigurationManager::getInstance(const string& host,
							unsigned short port)
{
	if (m_instance == 0)
	{
		m_instance = new ConfigurationManager(host, port);
	}
	return m_instance;
}

/**
 * Return all FogLAMP categories from storage layer
 *
 * @return	ConfigCategories class object with
 *		key and description for all found categories.
 * @throw	CategoryDetailsException exception
 */
ConfigCategories ConfigurationManager::getAllCategoryNames() const
{
	vector<Returns *> columns;
	columns.push_back(new Returns("key"));
	columns.push_back(new Returns("description"));
	Query qAllCategories(columns);

	// Query via Storage client
	ResultSet* allCategories = m_storage->queryTable("configuration", qAllCategories);
	if (!allCategories)
	{
		throw StorageOperationException();
	}

	ConfigCategories categories;

	for (ResultSet::RowIterator it = allCategories->firstRow(); ;)
	{
		ResultSet::Row* row = *it;
		if (!row)
		{
			delete allCategories;
			throw CategoryDetailsException();
		}	
		ResultSet::ColumnValue* key = row->getColumn("key");
		ResultSet::ColumnValue* description = row->getColumn("description");

		ConfigCategoryDescription *value = new ConfigCategoryDescription(key->getString(),
										 description->getString());

		// Add current row data to categories;
		categories.addCategoryDescription(value);
	
		if (allCategories->isLastRow(it))
		{
			break;
		}

		it++;
	}

	// Free result set
	delete allCategories;

	return categories;
}

/**
 * Return all the items of a specific category
 * from the storage layer.
 *
 * @param categoryName	The specified category name
 * @return		ConfigCategory calss object
 *			with all category items
 * @throw 		NoSuchCategoryException
 * @throw		Exception
 */

ConfigCategory ConfigurationManager::getCategoryAllItems(const string& categoryName) const
{
	// SELECT * FROM foglamp.configuration WHERE key = categoryName
	const Condition conditionKey(Equals);
	Where *wKey = new Where("key", conditionKey, categoryName);
	Query qKey(wKey);

	// Query via storage client
	ResultSet* categoryItems = m_storage->queryTable("configuration", qKey);
	if (!categoryItems)
	{
		throw StorageOperationException();
	}

	// Cayegory not found
	if (!categoryItems->rowCount())
	{
		delete categoryItems;
		throw NoSuchCategoryException();
	}

	// Get first row
	ResultSet::RowIterator it = categoryItems->firstRow();
	ResultSet::Row* row = *it;
	if (!row)
	{
		delete categoryItems;
		throw CategoryDetailsException();
	}	

	ResultSet::ColumnValue* key = row->getColumn("key");
	ResultSet::ColumnValue* description = row->getColumn("description");
	ResultSet::ColumnValue* items = row->getColumn("value");

	// Create string representation of JSON object
	rapidjson::StringBuffer buffer;
	rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);
	const rapidjson::Value *v = items->getJSON();
	v->Accept(writer);

	const string sItems(buffer.GetString(), buffer.GetSize());

	// Create category object
	ConfigCategory theVal(key->getString(), sItems);

	// Set description
	theVal.setDescription(description->getString());

	delete categoryItems;

	return theVal;
}

/**
 * Create or update a new category
 *
 * @param categoryName		The category name
 * @param categoryDescription	The category description
 * @param categoryItems		The category items
 * @return			The ConfigCategory object
 *				with "value" and "default"
 *				of the new category added
 *				or the merged configuration
 *				of the updated confguration.
 * @throw			CategoryDetailsException exception
 *				ConfigMalformed exception
 *				ConfigValueFoundWithDefault exception
 *				StorageOperationException exception
 *				Generic exception
 */

ConfigCategory ConfigurationManager::createCategory(const std::string& categoryName,
						    const std::string& categoryDescription,
						    const std::string& categoryItems) const
{
	// Fill the ready to insert category object with input data
	ConfigCategory preparedValue(categoryName, categoryItems);
	preparedValue.setDescription(categoryDescription);

	try
	{
		// Abort if items contain both value and default
		preparedValue.checkDefaultValuesOnly();

		// Add 'value' from 'default' for each item
		preparedValue.setItemsValueFromDefault();
	}
	catch (ConfigMalformed* e)
	{
		delete e;
		throw;
	}
	catch (ConfigValueFoundWithDefault* e)
	{
		delete e;
		throw;
	}
	catch (...)
	{
		throw;
	}

	// Parse JSON input
	Document doc;
	// Parse the prepared input category with "value" and "default"
	doc.Parse(preparedValue.itemsToJSON().c_str());
	if (doc.HasParseError())
	{
		throw new ConfigMalformed();
	}

	// Set the JSON string for merged category values
	string updatedItems;

	// SELECT * FROM foglamp.configuration WHERE key = categoryName
	const Condition conditionKey(Equals);
	Where *wKey = new Where("key", conditionKey, categoryName);
	Query qKey(wKey);

	// Query via storage client
	ResultSet* result = m_storage->queryTable("configuration", qKey);
	if (!result)
	{
		throw StorageOperationException();
	}

	if (!result->rowCount())
	{
		// Prepare insert values for insertTable
		InsertValues newCategory;
		newCategory.push_back(InsertValue("key", categoryName));
		newCategory.push_back(InsertValue("description", categoryDescription));
		// Set "value" field for inseert using the JSON document object
		newCategory.push_back(InsertValue("value", doc));

		// Do the insert
		if (!m_storage->insertTable("configuration", newCategory))
		{
			delete result;
			throw StorageOperationException();
		}
	}
	else
	{
		// The category already exists: fetch data
		ResultSet::RowIterator it = result->firstRow();
		ResultSet::Row* row = *it;
		if (!row)
		{
			delete result;
			throw CategoryDetailsException();
		}

		// Get current category items
		ResultSet::ColumnValue* theItems = row->getColumn("value");
		const Value* storedData = theItems->getJSON();

		// Prepare for merge
		Document::AllocatorType& allocator = doc.GetAllocator();
		Value inputValues = doc.GetObject();

		/** Merge input data with stored data:
		 * Note: stored configuration items are always replaced
		 * in this current implementation: no merge with found items.
		 * Items "value" are preserved for items being updated, only "default" values
		 * are overwritten.
		 */
		mergeCategoryValues(inputValues, storedData, allocator);

		// Create the new JSON string representation of merged category items
		rapidjson::StringBuffer buffer;
		rapidjson::Writer<rapidjson::StringBuffer> writer(buffer);

		// inputValues is the merged configuration
		inputValues.Accept(writer);

		// Set the JSON string with updated items
		updatedItems = string(buffer.GetString(), buffer.GetSize());

		// Prepare WHERE id = val
		const Condition conditionKey(Equals);
		Where wKey("key", conditionKey, categoryName);

		// Prepare insert values for updateTable
		InsertValues updateCategoryValues;
		updateCategoryValues.push_back(InsertValue("key", categoryName));
		updateCategoryValues.push_back(InsertValue("description", categoryDescription));

		// Add the "value" DB field for UPDATE (inputValuea with merged data)
		updateCategoryValues.push_back(InsertValue("value", inputValues));

		// Perform UPDATE foglamp.configuration SET value = x WHERE okey = y
		if (!m_storage->updateTable("configuration", updateCategoryValues, wKey))
		{
			delete result;
			throw StorageOperationException();
		}
	}

	bool returnNew = result->rowCount() == 0;

	// Free result set data
	delete result;

	if (returnNew)
	{
		// Return the new created category
		return preparedValue;
	}
	else
	{
		// Return the updated/merged category
		ConfigCategory returnValue(categoryName, updatedItems);
		returnValue.setDescription(categoryDescription);

		return  returnValue;
	}
}

/**
 * Merge the input data with stored data:
 *
 * NOTE:
 * the stored configuration items are always replaced
 * in this current implementation: there is no merge with found items.
 *
 * The confguration items "value" objects are preserved
 * for the item names being updated, only the "default" values
 * are overwritten.
 *
 * Examples:
 * "value" : {"item_1" : { "description" : "B", "type" : "string", "default" : "TWO" }
	      "item_7": { "description" : "Z", "type" : "string", "default" : "SEVEN" }}
 *
 * If "item_1" exists with "value" ONE and "default" ONE, the result is:
 * "value" : ONE, "default" : "TWO"
 * other fields in "item_1" are overwritten and any other item removed.
 *
 * if "item_1"  doesn't exist and current data is
 * "value" : {"item_0" : { "description" : "A", "type" : "string", "default" : "NONE" },
	      "item_7": { "description" : "Z", "type" : "string", "default" : "SEVEN" }}
 * that entry is completely replaced by the new one "value" : {"item_1" : { ...}}
 *
 *
 * @param newValues	JSON document with new inout configuration items
 * @param storedValues	Current stored values in storage layer
 */

void ConfigurationManager::mergeCategoryValues(Value& inputValues,
						const Value* storedValues,
						Document::AllocatorType& allocator) const
{
	// Loop throught input data
	for (Value::MemberIterator itr = inputValues.MemberBegin(); itr != inputValues.MemberEnd(); ++itr)
	{
		// Get current item name
		string itemName = itr->name.GetString();

		// Find the itemName "value" in the stored data
		Value::ConstMemberIterator storedItr = storedValues->FindMember(itemName.c_str());

		if (storedItr != storedValues->MemberEnd() && storedItr->value.IsObject())
		{
			// Remove current "value"
			itr->value.EraseMember("value");
			// Get itemName "value" in stored data
			auto& v = storedItr->value.GetObject()["value"];
			Value object;

			switch (v.GetType())
			{
				// String
				case (kStringType):
				{
					object.SetString(v.GetString(), allocator);
					itr->value.AddMember("value", object, allocator);

					break;
				}
				// Object
				case (kObjectType):
				{
					rapidjson::StringBuffer strbuf;
					rapidjson::Writer<rapidjson::StringBuffer> writer(strbuf);
					Value tmpObj;
					v.Accept(writer);
					object.SetString(strbuf.GetString(), allocator);
					itr->value.AddMember("value", object, allocator);

					break;
				}
				// Object & Array not supported yet
				default:
				{
					throw NotSupportedDataTypeException();
					break;
				}
			}
		}
	}
}

/**
 * Get a given item within a given category
 * @param categoryName	The given category
 * @param itemName	The given item 
 * @return		JSON string with item details
 */
string ConfigurationManager::getCategoryItem(const string& categoryName,
					     const string& itemName) const
{
	try
	{
		ConfigCategory allItems = this->getCategoryAllItems(categoryName);
		return allItems.itemToJSON(itemName);
	}
	catch (NoSuchCategoryException& e)
	{
	}
	catch (...)
	{
	}
	return "{}";
}

/**
 * Get the value of a given item within a given category
 * @param categoryName	The given category
 * @param itemName	The given item 
 * @return		string with item value
 */
string ConfigurationManager::getCategoryItemValue(const string& categoryName,
						  const string& itemName) const
{
	try
	{
		ConfigCategory allItems = this->getCategoryAllItems(categoryName);
		return allItems.getValue(itemName);
	}
	catch (NoSuchCategoryException& e)
	{
		// Category categoryName not found
	}
	catch (ConfigItemNotFound* e)
	{
		// Category item itemName not found
		delete e;
	}
	catch (...)
	{
	}
	return "";
}

/**
 * Set the "value" entry of a given item within a given category.
 *
 * @param categoryName	The given category
 * @param itemName	The given item
 * @param newValue	The "value" entry to set
 * @return		True on success, false on DB update error
 * @throw		NoSuchItemException exception
 *			if categoryName/itemName doesn't exist
 */

bool ConfigurationManager::setCategoryItemValue(const std::string& categoryName,
						const std::string& itemName,
						const std::string& newValue) const
{
	// Fetch itemName from categoryName
	string currentItemValue = this->getCategoryItemValue(categoryName, itemName);
	if (currentItemValue.empty())
	{
		string errMsg("No detail found for the category_name: " + categoryName);
		errMsg += " and config_item: " + itemName;

		throw NoSuchItemException(errMsg);
	}

	/**
	 * Check whether newValue is the same as currentValue
	 * NOTE:
	 * Does it work if newValue represents JSON object
	 * istead of a simple value?
	 */
	if (currentItemValue.compare(newValue) == 0)
	{
		// Same value: return success	
		return true;
	}

	// Prepare WHERE id = val
	const Condition conditionKey(Equals);
	Where wKey("key", conditionKey, categoryName);

	// Prepare jsonPropertis with one string vector: itemName, value
	vector<string> jsonPaths;
	jsonPaths.push_back(itemName);
	jsonPaths.push_back("value");
	JSONProperties jsonValues;
	jsonValues.push_back(JSONProperty("value", jsonPaths, newValue));

	// UPDATE foglamp.configuration SET vale = JSON(jsonValues)
	// WHERE key = 'categoryName';
	if (!m_storage->updateTable("configuration", jsonValues, wKey))
	{
		// Return failure
		return false;
	}

	// Return success	
	return true;
}

