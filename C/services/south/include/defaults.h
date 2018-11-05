#ifndef _DEFAULTS_H
#define _DEFAULTS_H
/*
 * FogLAMP reading ingest.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */

static struct {
	const char	*name;
	const char	*description;
	const char	*type;
	const char	*value;
} defaults[] = {
	{ "readingsPerSec",	"Number of readings to generate per sec",	"integer", "1" },
	{ "maxSendLatency",	"Maximum time to spend filling buffer before sending", "integer", "5000" },
	{ "bufferThreshold",	"Number of readings to buffer before sending", "integer", "100" },
	{ NULL, NULL, NULL, NULL }
};
#endif
