#ifndef _PLUGIN_API
#define _PLUGIN_API
/*
 * FogLAMP storage service.
 *
 * Copyright (c) 2017,2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
 
typedef struct {
        const char	*name;
        const char	*version;
        unsigned int	options;
        const char	*type;
        const char	*interface;
	const char	*config;
} PLUGIN_INFORMATION;
 
typedef struct {
        char         *message;
        char         *entryPoint;
        bool         retryable;
} PLUGIN_ERROR;
 
typedef void * PLUGIN_HANDLE;
 
/**
 * Plugin options bitmask values
 */
#define SP_COMMON       0x0001
#define SP_READINGS     0x0002
#define SP_ASYNC	0x0004
#define SP_PERSIST_DATA	0x0008
 
/**
 * Plugin types
 */
#define PLUGIN_TYPE_STORAGE			"storage"
#define PLUGIN_TYPE_SOUTH			"south"
#define PLUGIN_TYPE_NORTH			"north"
#define PLUGIN_TYPE_FILTER			"filter"
#define PLUGIN_TYPE_NOTIFICATION_RULE		"notificationRule"
#define PLUGIN_TYPE_NOTIFICATION_DELIVERY	"notificationDelivery"

#endif
