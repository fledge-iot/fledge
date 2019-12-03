#ifndef _NORTH_FILTER_PIPELINE_H
#define _NORTH_FILTER_PIPELINE_H
/*
 * Fledge filter pipeline class for sending process
 *
 * Copyright (c) 2019 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Amandeep Singh Arora
 */

#include <filter_pipeline.h>

/**
 * The NorthFilterPipeline class is derived from FilterPipeline class and 
 * is used to represent a pipeline of filter applicable to sending process. 
 * Methods are provided to load filters, setup filtering pipeline and for 
 * pipeline/filters cleanup.
 */
class NorthFilterPipeline : public FilterPipeline 
{

public:
	NorthFilterPipeline(ManagementClient* mgtClient, StorageClient& storage, std::string serviceName);
	~NorthFilterPipeline() {}
	
	// Setup the filter pipeline
	bool		setupFiltersPipeline(void *passToOnwardFilter, void *useFilteredData, void *sendingProcess);
};

#endif
