#ifndef _DEFAULTS_H
#define _DEFAULTS_H
/*
 * Fledge reading ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

// The maximum value a user will be allowed to set the maxSendLatency config item expressed in mS
#define MAXSENDLATENCY	600000	// 10 minutes

// The default advanced configuration items to add to the category
static struct {
	const char	*name;
	const char	*displayName;
	const char	*description;
	const char	*type;
	const char	*value;
} defaults[] = {
	{ "maxSendLatency",	"Maximum Reading Latency (mS)",
			"Maximum time to spend filling buffer before sending", "integer", "5000" },
	{ "bufferThreshold",	"Maximum buffered Readings",
			"Number of readings to buffer before sending", "integer", "100" },
	{ "throttle",	"Throttle",
			"Enable flow control by reducing the poll rate", "boolean", "false" },
	{ "readingsPerSec",	"Reading Rate",
			"Number of readings to generate per interval", "integer", "1" },
	{ "assetTrackerInterval",	"Asset Tracker Update",
			"Number of milliseconds between updates of the asset tracker information",
			"integer", "500" },
	{ NULL, NULL, NULL, NULL, NULL }
};
#endif
