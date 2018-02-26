/*
 * FogLAMP services common.
 *
 * Copyright (c) 2018 OSisoft, LLC
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

/**
 * Implementation of PluginNotImplementedException.
 * This exception should be thrown when a feature is not implemented yet.
 */
class PluginNotImplementedException : public std::exception {
public:
	// Construct with a default error message:
	PluginNotImplementedException(const char * error = "Functionality not implemented yet!")
	{
		errorMessage = error;
	}

	// Compatibility with std::exception.
	const char * what() const noexcept
	{
		return errorMessage.c_str();
	}

private:
        std::string errorMessage;
};
