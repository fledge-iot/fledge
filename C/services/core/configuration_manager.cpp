/*
 * FogLAMP FogLAMP Configuration management.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <sstream>
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
 * @throw	CategoryDetailsEx exception
 */
ConfigCategories ConfigurationManager::getAllCategoryNames() const
{
	// Return object
	ConfigCategories categories;

	vector<Returns *> columns;
	columns.push_back(new Returns("key"));
	columns.push_back(new Returns("description"));
	Query qAllCategories(columns);

	ResultSet* allCategories = 0;
	try
	{
		// Query via Storage client
		allCategories = m_storage->queryTable("configuration", qAllCategories);
		if (!allCategories || !allCategories->rowCount())
		{
			// Data layer error or no data to handle
			throw CategoryDetailsEx();
		}

		// Fetch all cetegories
		ResultSet::RowIterator it = allCategories->firstRow();
		do
		{
			ResultSet::Row* row = *it;
			if (!row)
			{
				throw CategoryDetailsEx();
			}	
			ResultSet::ColumnValue* key = row->getColumn("key");
			ResultSet::ColumnValue* description = row->getColumn("description");

			ConfigCategoryDescription *value = new ConfigCategoryDescription(key->getString(),
											 description->getString());
			// Add current row data to categories;
			categories.addCategoryDescription(value);

		} while (!allCategories->isLastRow(it++));

		// Free result set
		delete allCategories;

		// Return object
		return categories;

	}
	catch (std::exception* e)
	{
		delete e;
		if (allCategories)
		{
			// Free result set
			delete allCategories;
		}
		throw CategoryDetailsEx();
	}
	catch (...)
	{
		if (allCategories)
		{
			// Free result set
			delete allCategories;
		}
		throw CategoryDetailsEx();
	}
}

/**
 * Return all the items of a specific category
 * from the storage layer.
 *
 * @param categoryName	The specified category name
 * @return		ConfigCategory calss object
 *			with all category items
 * @throw 		NoSuchCategory exception
 * @throw		ConfigCategoryEx exception
 * @throw		CategoryDetailsEx exception
 */

ConfigCategory ConfigurationManager::getCategoryAllItems(const string& categoryName) const
{
	// SELECT * FROM foglamp.configuration WHERE key = categoryName
	const Condition conditionKey(Equals);
	Where *wKey = new Where("key", conditionKey, categoryName);
	Query qKey(wKey);

	ResultSet* categoryItems = 0;
	try
	{
		// Query via storage client
		categoryItems = m_storage->queryTable("configuration", qKey);
		if (!categoryItems)
		{
			throw ConfigCategoryEx();
		}

		// Category not found
		if (!categoryItems->rowCount())
		{
			throw NoSuchCategory();
		}

		// Get first row
		ResultSet::RowIterator it = categoryItems->firstRow();
		ResultSet::Row* row = *it;
		if (!row)
		{
			throw CategoryDetailsEx();
		}	

		// If we have an exception catch it and free the result set
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

		// Free result set
		delete categoryItems;

		return theVal;
	}
	catch (std::exception* e)
	{
		delete e;
		if (categoryItems)
		{
			// Free result set
			delete categoryItems;
		}
		throw ConfigCategoryEx();
	}
	catch (NoSuchCategory& e)
	{
		if (categoryItems)
		{
			// Free result set
			delete categoryItems;
		}
		throw;
	}
	catch (...)
	{
		if (categoryItems)
		{
			// Free result set
			delete categoryItems;
		}
		throw ConfigCategoryEx();
	}
}

/**
 * Create or update a new category
 *
 * @param categoryName		The category name
 * @param categoryDescription	The category description
 * @param categoryItems		The category items
 * @param keepOriginalItems	Keep stored iterms or replace them
 * @return			The ConfigCategory object
 *				with "value" and "default"
 *				of the new category added
 *				or the merged configuration
 *				of the updated confguration.
 * @throw			CategoryDetailsEx exception
 * @throw			ConfigCategoryEx exception
 * @throw			ConfigCategoryDefaultWithValue exception
 */

ConfigCategory ConfigurationManager::createCategory(const std::string& categoryName,
						    const std::string& categoryDescription,
						    const std::string& categoryItems,
						    bool keepOriginalItems) const
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
		throw ConfigCategoryEx();
	}
	catch (ConfigValueFoundWithDefault* e)
	{
		// The category items have both default and value properties
		// raise the ConfigCategoryDefaultWithValue exception;
		delete e;

		// Raise specific exception
		throw ConfigCategoryDefaultWithValue();
	}
	catch (std::exception* e)
	{
		delete e;
		throw ConfigCategoryEx();
	}
	catch (...)
	{
		throw ConfigCategoryEx();
	}

	// Parse JSON input
	Document doc;
	// Parse the prepared input category with "value" and "default"
	doc.Parse(preparedValue.itemsToJSON().c_str());
	if (doc.HasParseError())
	{
		throw ConfigCategoryEx();
	}

	// Set the JSON string for merged category values
	string updatedItems;

	// SELECT * FROM foglamp.configuration WHERE key = categoryName
	const Condition conditionKey(Equals);
	Where *wKey = new Where("key", conditionKey, categoryName);
	Query qKey(wKey);

	ResultSet* result = 0;
	try
	{
		// Query via storage client
		result = m_storage->queryTable("configuration", qKey);
		if (!result)
		{
			throw ConfigCategoryEx();
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
				throw ConfigCategoryEx();
			}
		}
		else
		{
			// The category already exists: fetch data
			ResultSet::RowIterator it = result->firstRow();
			ResultSet::Row* row = *it;
			if (!row)
			{
				throw CategoryDetailsEx();
			}

			// Get current category items
			ResultSet::ColumnValue* theItems = row->getColumn("value");
			const Value* storedData = theItems->getJSON();

			// Prepare for merge
			Document::AllocatorType& allocator = doc.GetAllocator();
			Value inputValues = doc.GetObject();

			/**
			 * Merge input data with stored data:
			 * stored configuration items are merged or replaced
			 * accordingly to keepOriginalItems parameter value.
			 *
			 * Items "value" are preserved for items being updated, only "default" values
			 * are overwritten.
			 */
			mergeCategoryValues(inputValues,
					    storedData,
					    allocator,
					    keepOriginalItems);

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
				throw ConfigCategoryEx();
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
	catch (std::exception* e)
	{
		delete e;
		if (result)
		{
			// Free result set
			delete result;
		}
		throw ConfigCategoryEx();
	}
	catch (...)
	{
		if (result)
		{
			// Free result set
			delete result;
		}
		throw ConfigCategoryEx();
	}
}

/**
 * Merge the input data with stored data:
 *
 * The stored configuration items are merged with new ones if
 * paramter keepOriginalItems is true otherwise they are replaced.
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
 * @param inputValues		New inout configuration items
 * @param storedValues		Current stored items in storage layer
 * @param keepOriginalItems	Keep stored items or replace them
 * @throw			NotSupportedDataType exception
 */

void ConfigurationManager::mergeCategoryValues(Value& inputValues,
						const Value* storedValues,
						Document::AllocatorType& allocator,
						bool keepOriginalItems) const
{
	// Loop throught input data
	// For each item fetch the value of stored one, if existent
	for (Value::MemberIterator itr = inputValues.MemberBegin(); itr != inputValues.MemberEnd(); ++itr)
	{
		// Get current item name
		string itemName = itr->name.GetString();

		// Find the itemName "value" in the stored data
		Value::ConstMemberIterator storedItr = storedValues->FindMember(itemName.c_str());

		if (storedItr != storedValues->MemberEnd() && storedItr->value.IsObject())
		{
			// Item name is present in stored data

			// 1. Remove current "value"
			itr->value.EraseMember("value");
			// 2. Get itemName "value" in stored data
			auto& v = storedItr->value.GetObject()["value"];
			Value object;

			// 3. Set new value
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
					v.Accept(writer);
					object.SetString(strbuf.GetString(), allocator);
					itr->value.AddMember("value", object, allocator);

					break;
				}
				//  Array and numbers not supported yet
				default:
				{
					throw NotSupportedDataType();
					break;
				}
			}
		}
	}

	// Add stored items not found in input items only if we want to keep them.
	if (keepOriginalItems == true)
	{
		Value::ConstMemberIterator itr;

		// Loop throught stored data
		for (itr = storedValues->MemberBegin(); itr != storedValues->MemberEnd(); ++itr )
		{
			string itemName = itr->name.GetString();

			// Find the itemName in the inout data
			Value::MemberIterator inputItr = inputValues.FindMember(itemName.c_str());

			if (inputItr == inputValues.MemberEnd())
			{
				// Set item name
				Value name(itemName.c_str(), allocator);
				
				Value object;
				object.SetObject();
				// Object copy
				object.CopyFrom(itr->value, allocator);
				
				// Add the new object
				inputValues.AddMember(name, object, allocator);
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
	ConfigCategory allItems = this->getCategoryAllItems(categoryName);
	return allItems.itemToJSON(itemName);
}

/**
 * Get the value of a given item within a given category
 * @param categoryName	The given category
 * @param itemName	The given item 
 * @return		string with item value
 * @throw		NoSuchCategoryItemValue exception
 */
string ConfigurationManager::getCategoryItemValue(const string& categoryName,
						  const string& itemName) const
{
	try
	{
		ConfigCategory allItems = this->getCategoryAllItems(categoryName);
		return allItems.getValue(itemName);
	}
	catch (std::exception* e)
	{
		//catch pointer exceptions)
		delete e;
		throw NoSuchCategoryItemValue();
	}
	catch (...)
	{
		// General catch
		throw NoSuchCategoryItemValue();
	}
}

/**
 * Set the "value" entry of a given item within a given category.
 *
 * @param categoryName	The given category
 * @param itemName	The given item
 * @param newValue	The "value" entry to set
 * @return		True on success.
 *			False on DB update error or storage layer exception
 *			
 * @throw		NoSuchCategoryItem exception
 *			if categoryName/itemName doesn't exist
 */
bool ConfigurationManager::setCategoryItemValue(const std::string& categoryName,
						const std::string& itemName,
						const std::string& newValue) const
{
	// Fetch itemName from categoryName
	string currentItemValue;
	try
	{
		currentItemValue = this->getCategoryItemValue(categoryName, itemName);
	}
	catch (...)
	{
		string errMsg("No details found for the category_name: " + categoryName);
		errMsg += " and config_item: " + itemName;

		throw NoSuchCategoryItem(errMsg);
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

	try
	{
		// UPDATE foglamp.configuration SET vale = JSON(jsonValues)
		// WHERE key = 'categoryName';
		return (!m_storage->updateTable("configuration", jsonValues, wKey)) ? false : true;
	}
	catch (std::exception* e)
	{
		delete e;
		// Return failure
		return false;
	}
	catch (...)
	{
		// Return failure
		return false;
	}
}

/**
 * Add child categories under a given (parent) category
 *
 * @param parentCategoryName	The parent category name
 * @param childCategories	The child categories list (JSON array)
 * @return			The JSON string with all (old and new) child
 *				categories of the parent category name
 * @throw			ChildCategoriesEx exception
 * @throw			ExistingChildCategories exception
 * @thow			NoSuchCategory exception
 */
string ConfigurationManager::addChildCategory(const string& parentCategoryName,
					      const string& childCategories) const
{
	// Check first parent category exists
	try
	{
		this->getCategoryAllItems(parentCategoryName);
	}
	catch (...)
	{
		throw NoSuchCategory();
	}

	// Parse JSON input
	Document doc;
	// Parse the prepared input category with "value" and "default"
	doc.Parse(childCategories.c_str());
	if (doc.HasParseError())
	{
		throw ChildCategoriesEx();
	}

	Value& children = doc["children"];
	if (!children.IsArray())
	{
		throw ChildCategoriesEx();
	}

	unsigned int rowsAdded = 0;

	ResultSet* categoryItems = 0;

	for (Value::ConstValueIterator itr = children.Begin(); itr != children.End(); ++itr)
	{
		if (!(*itr).IsString())
		{       
			throw ChildCategoriesEx();
		}

		string childCategory = (*itr).GetString();

		// Note: all "children" categories must exist
		// SELECT * FROM foglamp.configuration WHERE key = categoryName
		const Condition conditionKey(Equals);
		Where *wKey = new Where("key", conditionKey, childCategory);
		Query qKey(wKey);

		try
		{
			// Query via storage client
			categoryItems = m_storage->queryTable("configuration", qKey);
			if (!categoryItems)
			{
				throw ChildCategoriesEx();
			}

			// Child category not found. throw exception
			if (!categoryItems->rowCount())
			{
				throw NoSuchCategory();
			}

			// Free result set
			delete categoryItems;

			// Check whether parent/child row already exists
			const Condition conditionParent(Equals);
			// Build the parent AND child WHHERE
			Where *wChild = new Where("child", conditionParent, childCategory);
			Where *wParent = new Where("parent", conditionParent, parentCategoryName, wChild);
			Query qParentChild(wParent);

			// Query via storage client
			categoryItems = m_storage->queryTable("category_children", qParentChild);
			if (!categoryItems)
			{
				throw ChildCategoriesEx();
			}

			// Parent/child has been found: skip the insert
			if (categoryItems->rowCount())
			{
				// Free result set
				delete categoryItems;
				continue;
			}

			// Free result set
			delete categoryItems;

			// Prepare insert values for insertTable
			InsertValues newCategory;
			newCategory.push_back(InsertValue("parent", parentCategoryName));
			newCategory.push_back(InsertValue("child", (*itr).GetString()));

			/**
			 * Do the insert:
			 * we don't check for failed result as we checked
			 * parent/child presence above
			 */
			m_storage->insertTable("category_children", newCategory);

			// Increment counter
			rowsAdded++;
		}
		catch (std::exception* e)
		{
			delete e;
			if (categoryItems)
			{
				// Free result set
				delete categoryItems;
			}
			throw ChildCategoriesEx();
		}
		catch (NoSuchCategory& e)
		{
			if (categoryItems)
			{
				// Free result set
				delete categoryItems;
			}
			throw;
		}
		catch (...)
		{
			if (categoryItems)
			{
				// Free result set
				delete categoryItems;
			}
			throw ChildCategoriesEx();
		}
	}

	// If no rows have been inserted, then abort
	if (!rowsAdded)
	{
		throw ExistingChildCategories();
	}

	// Fetch current children of parentCategoryName;
	return this->fetchChildCategories(parentCategoryName);
}

/**
 * Fetch all child categories of a given parent one
 * @param parentCategoryName	The given category name
 * @return			JSON array string with child categories
 * @throw			ChildCategoriesEx exception
 */
string ConfigurationManager::fetchChildCategories(const string& parentCategoryName) const
{
	ostringstream currentChildCategories;

	// Fetch current children of parentCategoryName;
	// SELECT * FROM foglamp.category_children WHERE parent = 'parentCategoryName'
	const Condition conditionCurrent(Equals);
	Where *wCurrent = new Where("parent", conditionCurrent, parentCategoryName);
	Query qCurrent(wCurrent);

	ResultSet* newCategories = 0;
	try
	{
		// Fetch all child categories
		newCategories = m_storage->queryTable("category_children", qCurrent);
		if (!newCategories)
		{	
			throw ChildCategoriesEx();
		}
		// Build ther JSON output
		currentChildCategories << "{ \"children\" : [ ";

		// If no child categories return empty array
		if (!newCategories->rowCount())
		{
			delete newCategories;
			currentChildCategories << " ] }";

			return currentChildCategories.str();
		}

		// We have some data
        	ResultSet::RowIterator it = newCategories->firstRow();
		do
        	{
                	ResultSet::Row* row = *it;
                	if (!row)
                	{
				throw ChildCategoriesEx();
        	        }

			// Add the child category to output result
               		ResultSet::ColumnValue* child = row->getColumn("child");
			currentChildCategories << "\"";
			currentChildCategories << child->getString();
			currentChildCategories << "\"";
			if (!newCategories->isLastRow(it))
			{
				currentChildCategories << ", ";
			}
		} while (!newCategories->isLastRow(it++));

		currentChildCategories << " ] }";

		// Free result set
		delete newCategories;

		// Returm child categories
		return currentChildCategories.str();
	}
	catch (std::exception* e)
	{
		delete e;
		if (newCategories)
		{
			delete newCategories;
		}
		throw ChildCategoriesEx();
	}
	catch (...)
	{
		if (newCategories)
		{
			delete newCategories;
		}
		throw ChildCategoriesEx();
	}
}

/**
 * Get all the child categories of a given category name
 *
 * @param parentCategoryName	The given category name
 * @return 			A ConfigCategories object
 *				with child categories (name and description)
 * @throw			ChildCategoriesEx exception
 */
ConfigCategories ConfigurationManager::getChildCategories(const string& parentCategoryName) const
{
	ConfigCategories categories;

	try
	{
		// Fetch all child categories
		string childCategories = this->fetchChildCategories(parentCategoryName);

		// Parse JSON input
		Document doc;
		// Parse the prepared input category with "value" and "default"
		doc.Parse(childCategories.c_str());

		if (doc.HasParseError() || !doc.HasMember("children"))
		{
			throw ChildCategoriesEx();
		}

		// Get child categories
		Value& children = doc["children"];
		if (!children.IsArray())
		{
			throw ChildCategoriesEx();
		}

		/**
		 * For each element fetch then category description
		 * and add the entry to ConfigCategories result
		 */
		for (Value::ConstValueIterator itr = children.Begin(); itr != children.End(); ++itr)
		{
			string categoryDesc;
			// Description must be a string
			if (!(*itr).IsString())
			{
				throw ChildCategoriesEx();
			}
			string categoryName = (*itr).GetString();

			// Fetch description
			categoryDesc = this->getCategoryDescription(categoryName);
			ConfigCategoryDescription *value = new ConfigCategoryDescription(categoryName,
											 categoryDesc);
			// Add current row data to categories;
			categories.addCategoryDescription(value);
		}

		// Return ConfigCategories object
		return categories;
	}
	catch (std::exception* e)
	{
		delete e;
		throw ChildCategoriesEx();
	}
	catch (...)
	{
		throw ChildCategoriesEx();
	}
}

/**
 * Get the categpry description of a given category
 *
 * @param categoryName	The given category
 * @return		The category description
 */
string ConfigurationManager::getCategoryDescription(const string& categoryName) const
{
	// Note:
	// Any throw exception that must be catched by the caller
	ConfigCategory currentCategory = this->getCategoryAllItems(categoryName);
	return currentCategory.getDescription();
}

/**
 * Remove the link between a child category and its parent.
 * The child becomes a root category when the link is broken.
 * Note the child category still exists after this call is made.
 *
 * @param parentCategoryName	The parennt category
 * @param childCategory		The child category to remove
 * @return			JSON array string with remaining
 *				child categories
 * @throw			ChildCategoriesEx exception
 */
string ConfigurationManager::deleteChildCategory(const string& parentCategoryName,
						 const string& childCategory) const
{
	const Condition conditionParent(Equals);
	// Build the parent AND child WHHERE
	Where* wChild = new Where("child", conditionParent, childCategory);
	Where* wParent = new Where("parent", conditionParent, parentCategoryName, wChild);
	Query qParentChild(wParent);

	try
	{
		// Do the delete
		int deletedRows = m_storage->deleteTable("category_children", qParentChild);
		if (deletedRows == -1)
		{
			throw ChildCategoriesEx();
		}
		return this->fetchChildCategories(parentCategoryName);
	}
	catch (std::exception* e)
	{
		delete e;
		throw ChildCategoriesEx();
	}
	catch (...)
	{
		throw ChildCategoriesEx();
	}
}

/**
 * Unset the category item value.
 *
 * @param categoryName		The category name
 * @param itemName		The item name
 * @return			JSON string of category item
 * @throw			ConfigCategoryEx exception
 * @throw			NoSuchCategoryItem exception
 */
string ConfigurationManager::deleteCategoryItemValue(const string& categoryName,
						     const string& itemName) const
{
	try
	{
		// Set the empty value
		if (!this->setCategoryItemValue(categoryName, itemName, ""))
		{
			throw ConfigCategoryEx();
		}
		// Return category item
		return this->getCategoryItem(categoryName, itemName);
	}
	catch (NoSuchCategoryItem& e)
	{
		throw;
	}
	catch (...)
	{
		throw ConfigCategoryEx();
	}
}

/**
 * Delete a category from database.
 * Also remove the link between a child category and its parent.
 *
 * @param categoryName	The category being deleted
 * @return		The remaining config categories as object
 * @throw		NoSuchCategory exception
 * @throw		ConfigCategoryEx exception
 */
ConfigCategories ConfigurationManager::deleteCategory(const string& categoryName) const
{
	const Condition conditionDelete(Equals);
	// Build WHERE key = 'categoryName'
	Where* wDelete = new Where("key", conditionDelete, categoryName);

	// Build the WHERE parent = 'categoryName'
	Where* wParent = new Where("parent", conditionDelete, categoryName);

	// DELETE from configuration
	Query qDelete(wDelete);
	// DELETE from category_children
	Query qParent(wParent);

	try
	{
		// Do the category delete
		int deletedRows = m_storage->deleteTable("configuration", qDelete);
		if (deletedRows == 0)
		{
			throw NoSuchCategory();
		}
		else
		{
			if (deletedRows == -1)
			{
				throw ConfigCategoryEx();
			}
		}

		// Do the child categores delete
		deletedRows = m_storage->deleteTable("category_children", qParent);
		if (deletedRows < 0)
		{
			throw ConfigCategoryEx();
		}
		else
		{
			return getAllCategoryNames();
		}
	}
	catch (NoSuchCategory& ex)
	{
		throw;
	}
	catch (...)
	{
		throw ConfigCategoryEx();
	}
}
