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
	{ "pollInterval",	"Wait time between polls of the device (ms)",	"integer", "1000" },
	{ "maxSendLatency",	"Maximum time to spend filling buffer before sending", "integer", "5000" },
	{ "bufferThreshold",	"Number of readings to buffer before sending", "integer", "100" },
	{ NULL, NULL, NULL, NULL }
};
#endif
