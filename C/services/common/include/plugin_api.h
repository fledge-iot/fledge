#ifndef _PLUGIN_API
#define _PLUGIN_API
/*
 * Fledge storage service.
 *
 * Copyright (c) 2017,2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch, Massimiliano Pinto
 */
#include <string>

#define TO_STRING(...) DEFER(TO_STRING_)(__VA_ARGS__)
#define DEFER(x) x
#define TO_STRING_(...) #__VA_ARGS__
#define QUOTE(...) TO_STRING(__VA_ARGS__)

/**
 * The plugin infiornation structure, used to return information
 * from a plugin during the laod and configuration stage.
 */
typedef struct {
	/** The name of the plugin */
        const char	*name;
	/** The release version of the plugin */
        const char	*version;
	/** The set of option flags that apply to this plugin */
        unsigned int	options;
	/**
	 * The plugin type, this is one of storage, south, 
	 * filter, north, notificationRule or notificationDelivery
	 */
        const char	*type;
	/** The interface version of this plugin */
        const char	*interface;
	/** The default JSON configuration category for this plugin */
	const char	*config;
} PLUGIN_INFORMATION;

/**
 * Structure used by plugins to return error information
 */
typedef struct {
        char         *message;
        char         *entryPoint;
        bool         retryable;
} PLUGIN_ERROR;

/**
 * Pass a name/value pair to a plugin
 */
typedef struct plugin_parameter {
	std::string	name;
	std::string	value;
} PLUGIN_PARAMETER;

/**
 * The handle used to reference a plugin. This is an opaque data
 * pointer and is used by the plugins as a way to pass information
 * between each invocation of the plugin entry points.
 */
typedef void * PLUGIN_HANDLE;

/**
 * The destinations to which control messages may be sent
 */
typedef enum controlDestination {
	/** The control message is destined for the source of a particular asset */
	DestinationAsset,
	/** The control message is destined for the named service */
	DestinationService,
	/** The control message is destined for all south services that support control */
	DestinationBroadcast,
	/** The control message is destined to execute the named script */
	DestinationScript
} ControlDestination;
 
/**
 * Plugin options bitmask values
 */
#define SP_COMMON		0x0001
#define SP_READINGS		0x0002
/** The plugin ingests data asynchronously */
#define SP_ASYNC		0x0004
/** The plugin wishes to persist data between executions */
#define SP_PERSIST_DATA		0x0008
/** The notification delivery plugin wishes to add (ingest) new data into the system */
#define SP_INGEST		0x0010
/** The plugin requires access to the Microservice Management API */
#define SP_GET_MANAGEMENT	0x0020
/** The plugin requires direct access to the storage service */
#define SP_GET_STORAGE		0x0040
/** The plugin has been deprecated and will be removed in a future release */
#define SP_DEPRECATED		0x0080
/** The plugin is built in and not installed be a seperate package */
#define SP_BUILTIN		0x0100
/** The plugin supports control data */
#define SP_CONTROL		0x1000

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
