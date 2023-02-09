#ifndef INCLUDE_DATAPOINT_UTILITY_H_
#define INCLUDE_DATAPOINT_UTILITY_H_
/*
 * Fledge
 *
 * Copyright (c) 2021 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Yannick Marchetaux
 * 
 */

#include <vector>
#include <string>
#include "datapoint.h"
#include "reading.h"

namespace DatapointUtility {  
	// Define type
	using Datapoints	= std::vector<Datapoint*>;
	using Readings		= std::vector<Reading*>;

	// Function for search value
	Datapoints		*findDictElement		(Datapoints* dict, const std::string& key);
	DatapointValue 	*findValueElement		(Datapoints* dict, const std::string& key);
	Datapoint	  	*findDatapointElement	(Datapoints* dict, const std::string& key);
	Datapoints		*findDictOrListElement	(Datapoints *dict, const std::string& key, DatapointValue::dataTagType type);
	Datapoints		*findListElement		(Datapoints *dict, const std::string& key);
	std::string	 	findStringElement		(Datapoints* dict, const std::string& key);

	// delete
	void deleteValue(Datapoints *dps, const std::string& key);

	// Function for create element
	Datapoint *createStringElement  	(Datapoints *dps, const std::string& key, const std::string& valueDefault);
	Datapoint *createIntegerElement 	(Datapoints *dps, const std::string& key, long valueDefault);
	Datapoint *createDictElement		(Datapoints *dps, const std::string& key);
	Datapoint *createListElement		(Datapoints *dps, const std::string& key);
	Datapoint *createDictOrListElement	(Datapoints* dps, const std::string& key, bool dict);
};

#endif  // INCLUDE_DATAPOINT_UTILITY_H_