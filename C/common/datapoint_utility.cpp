/*
 * Datapoint utility.
 *
 * Copyright (c) 2020, RTE (https://www.rte-france.com)
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Yannick Marchetaux
 * 
 */
#include <datapoint_utility.h>
#include <vector>

using namespace std;

/**
 * Search a dictionary from a key
 *
 * @param dict : parent dictionary
 * @param key : key to research
 * @return vector of datapoint otherwise null pointer
*/
DatapointUtility::Datapoints *DatapointUtility::findDictElement(Datapoints *dict, const string& key) {
	return findDictOrListElement(dict, key, DatapointValue::T_DP_DICT);
}

/**
 * Search a array from a key
 *
 * @param dict : parent dictionary
 * @param key : key to research
 * @return vector of datapoint otherwise null pointer
*/
DatapointUtility::Datapoints *DatapointUtility::findListElement(Datapoints *dict, const string& key) {
	return findDictOrListElement(dict, key, DatapointValue::T_DP_LIST);
}

/**
 * Search a list or dictionary from a key
 *
 * @param dict : parent dictionary
 * @param key : key to research
 * @param type : type of data searched
 * @return vector of datapoint otherwise null pointer
*/
DatapointUtility::Datapoints *DatapointUtility::findDictOrListElement(Datapoints *dict, const string& key, DatapointValue::dataTagType type) {
	Datapoint *dp = findDatapointElement(dict, key);
	
	if (dp == nullptr) {
		return nullptr;
	}

	DatapointValue& data = dp->getData();
	if (data.getType() == type) {
		return data.getDpVec();
	}
	
	return nullptr;
}

/**
 * Search a DatapointValue from a key
 *
 * @param dict : parent dictionary
 * @param key : key to research 
 * @return corresponding datapointValue otherwise null pointer
*/
DatapointValue *DatapointUtility::findValueElement(Datapoints *dict, const string& key) {
	
	Datapoint *dp = findDatapointElement(dict, key);
	
	if (dp == nullptr) {
		return nullptr;
	}

	return &dp->getData();
}

/**
 * Search a Datapoint from a key
 *
 * @param dict : parent dictionary
 * @param key : key to research
 * @return corresponding datapoint otherwise null pointer
*/
Datapoint *DatapointUtility::findDatapointElement(Datapoints *dict, const string& key) {
	if (dict == nullptr) {
		return nullptr;
	}
	
	for (Datapoint *dp : *dict) {
		if (dp->getName() == key) {
			return dp;
		}
	}
	return nullptr;
}

/**
 * Search a string from a key
 *
 * @param dict : parent dictionary
 * @param key : key to research
 * @return corresponding string otherwise empty string
*/
string DatapointUtility::findStringElement(Datapoints *dict, const string& key) {
	
	Datapoint *dp = findDatapointElement(dict, key);
	
	if (dp == nullptr) {
		return "";
	}

	DatapointValue& data = dp->getData();
	const DatapointValue::dataTagType dType(data.getType());
	if (dType == DatapointValue::T_STRING) {
		return data.toStringValue();
	}

	return "";
}

/**
 * Method to delete and to free elements from a vector
 * 
 * @param dps dict of values 
 * @param key key of dict 
*/
void DatapointUtility::deleteValue(Datapoints *dps, const string& key) {
	for (Datapoints::iterator it = dps->begin(); it != dps->end(); it++){
		if ((*it)->getName() == key) {
			delete (*it);
			dps->erase(it);
			break;
		}
	}
}

/**
 * Generate default attribute integer on Datapoint
 * 
 * @param dps dict of values 
 * @param key key of dict
 * @param valueDefault value attribute of dict
 * @return pointer of the created datapoint
 */
Datapoint *DatapointUtility::createIntegerElement(Datapoints *dps, const string& key, long valueDefault) {

	deleteValue(dps, key);

	DatapointValue dv(valueDefault);
	Datapoint *dp = new Datapoint(key, dv);
	dps->push_back(dp);

	return dp;
}

/**
 * Generate default attribute string on Datapoint
 * 
 * @param dps dict of values 
 * @param key key of dict
 * @param valueDefault value attribute of dict
 * @return pointer of the created datapoint
 */
Datapoint *DatapointUtility::createStringElement(Datapoints *dps, const string& key, const string& valueDefault) {

	deleteValue(dps, key);

	DatapointValue dv(valueDefault);
	Datapoint *dp = new Datapoint(key, dv);
	dps->push_back(dp);

	return dp;
}

/**
 * Generate default attribute dict on Datapoint
 * 
 * @param dps dict of values 
 * @param key key of dict
 * @param dict if the element is a dictionary
 * @return pointer of the created datapoint
 */
Datapoint *DatapointUtility::createDictOrListElement(Datapoints* dps, const string& key, bool dict) {

	deleteValue(dps, key);

	Datapoints *newVec = new Datapoints;
	DatapointValue dv(newVec, dict);
	Datapoint *dp = new Datapoint(key, dv);
	dps->push_back(dp);

	return dp;
}

/**
 * Generate default attribute dict on Datapoint
 * 
 * @param dps dict of values 
 * @param key key of dict
 * @return pointer of the created datapoint
 */
Datapoint *DatapointUtility::createDictElement(Datapoints* dps, const string& key) {
	return createDictOrListElement(dps, key, true);
}

/**
 * Generate default attribute list on Datapoint
 * 
 * @param dps dict of values 
 * @param key key of dict
 * @return pointer of the created datapoint
 */
Datapoint *DatapointUtility::createListElement(Datapoints* dps, const string& key) {
   return createDictOrListElement(dps, key, false);
}