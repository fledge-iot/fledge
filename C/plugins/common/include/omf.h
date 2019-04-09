#ifndef _OMF_H
#define _OMF_H
/*
 * FogLAMP OSI Soft OMF interface to PI Server.
 *
 * Copyright (c) 2018 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */
#include <string>
#include <vector>
#include <map>
#include <reading.h>
#include <http_sender.h>
#include <zlib.h>

#define TYPE_ID_DEFAULT 1
#define FAKE_ASSET_KEY "_default_start_id_"
#define OMF_TYPE_STRING  "string"
#define OMF_TYPE_INTEGER "integer"
#define OMF_TYPE_FLOAT   "number"

/**
 * Per asset dataTypes
 *
 * typeId is a prefix for OMF data Type messages
 * types is a JSON string with datapoint names and types
 * This class is used in a std::map where assetName is a key
 */
class OMFDataTypes
{
        public:
                long typeId;
                std::string types;
};

/**
 * The OMF class.
 */
class OMF
{
        public:
		/**
		 * Constructor:
		 * pass server URL path, OMF_type_id and producerToken.
		 */
		OMF(HttpSender& sender,
                    const std::string& path,
		    const long typeId,
		    const std::string& producerToken);

		OMF(HttpSender& sender,
		    const std::string& path,
		    std::map<std::string, OMFDataTypes>& types,
		    const std::string& producerToken);

		// Destructor
		~OMF();

		/**
		 * Send data to PI Server passing a vector of readings.
		 *
		 * Data sending is composed by a few phases
		 * handled by private methods.
		 *
		 * Note: DataTypes are sent only once by using
		 * an in memory key map, being the key = assetName + typeId.
		 * Passing false to skipSentDataTypes changes the logic.
		 *
		 * Returns the number of processed readings.
		 */

		// Method with vector (by reference) of readings
		uint32_t sendToServer(const std::vector<Reading>& readings,
				      bool skipSentDataTypes = true);

		// Method with vector (by reference) of reading pointers
		uint32_t sendToServer(const std::vector<Reading *>& readings,
				      bool compression, bool skipSentDataTypes = true);

		// Send a single reading (by reference)
		uint32_t sendToServer(const Reading& reading,
				      bool skipSentDataTypes = true);

		// Send a single reading pointer
		uint32_t sendToServer(const Reading* reading,
				      bool skipSentDataTypes = true);

		// Set saved OMF formats
		void setFormatType(const std::string &key, std::string &value);

		// Get saved OMF formats
		std::string getFormatType(const std::string &key) const;

		// Set the list of errors considered not blocking
		// in the communication with the PI Server
                void setNotBlockingErrors(std::vector<std::string>& );

		// Compress string using gzip
		std::string compress_string(const std::string& str,
                            				int compressionlevel = Z_DEFAULT_COMPRESSION);

		// Return current value of global type-id
		const long getTypeId() const { return m_typeId; };

		// Check DataTypeError
		bool isDataTypeError(const char* message);

		// Map object types found in input data
		void setMapObjectTypes(const std::vector<Reading *>& data,
					std::map<std::string, Reading*>& dataSuperSet) const;
		// Removed mapped object types found in input data
		void unsetMapObjectTypes(std::map<std::string, Reading*>& dataSuperSet) const;

		void setStaticData(std::vector<std::pair<std::string, std::string>> *staticData)
		{
			m_staticData = staticData;
		};

	private:
		/**
		 * Builds the HTTP header to send
		 * messagetype header takes the passed type value:
		 * 'Type', 'Container', 'Data'
		 */
		const std::vector<std::pair<std::string, std::string>>
			createMessageHeader(const std::string& type) const;

		// Create data for Type message for current row
		const std::string createTypeData(const Reading& reading) const;

		// Create data for Container message for current row
		const std::string createContainerData(const Reading& reading) const;

		// Create data for additional type message, with 'Data' for current row
		const std::string createStaticData(const Reading& reading) const;

		// Create data Link message, with 'Data', for current row
		const std::string createLinkData(const Reading& reading) const;

		/**
		 * Creata data for readings data content, with 'Data', for one row
		 * The new formatted data have to be added to a new JSON doc to send.
		 * we want to avoid sending of one data row
		 */
		const std::string createMessageData(Reading& reading);

		// Set the the tagName in an assetName Type message
		void setAssetTypeTag(const std::string& assetName,
				     const std::string& tagName,
				     std::string& data) const;

		// Create the OMF data types if needed
		bool handleDataTypes(const Reading& row,
				     bool skipSendingTypes);

		// Send OMF data types
		bool sendDataTypes(const Reading& row);

		// Get saved dataType
		bool getCreatedTypes(const std::string& key);

		// Set saved dataType
		bool setCreatedTypes(const std::string& key);

		// Clear data types cache
		void clearCreatedTypes();

		// Increment type-id value
		void incrementTypeId();

                // Handle data type errors
		bool handleTypeErrors(const Reading& reading);

		// Extract assetName from erro message
		std::string getAssetNameFromError(const char* message);

		// Get asset type-id from cached data
		long getAssetTypeId(const std::string& assetName) const;

		// Increment per asset type-id value
		void incrementAssetTypeId(const std::string& assetName);

		// Set global type-id as the maximum value of all per asset type-ids
		void setTypeId();

		// Set saved dataType
		bool setCreatedTypes(const Reading& row);

		// Remove cached data types enttry for given asset name
		void clearCreatedTypes(const std::string& key);

	private:
		const std::string	m_path;
		long			m_typeId;
		const std::string	m_producerToken;

		// Define the OMF format to use for each type
		// the format will not be applied if the string is empty
                std::map<const std::string, std::string> m_formatTypes {
			{OMF_TYPE_STRING, ""},
			{OMF_TYPE_INTEGER,"int64"},
			{OMF_TYPE_FLOAT,  "float64"}
		};

    		// Vector with OMF_TYPES
		const std::vector<std::string> omfTypes = { OMF_TYPE_STRING,
							    OMF_TYPE_FLOAT,  // Forces the creation of float also for integer numbers
							    OMF_TYPE_FLOAT };
		// HTTP Sender interface
		HttpSender&		m_sender;
		bool			m_lastError;
		bool			m_changeTypeId;

		// These errors are considered not blocking in the communication
		// with the destination, the sending operation will proceed
		// with the next block of data if one of these is encountered
		std::vector<std::string> m_notBlockingErrors;

		// Data types cache[key] = (key_type_id, key data types)
		std::map<std::string, OMFDataTypes>*
					m_OMFDataTypes;
		/**
		 * Static data to send to OMF
		 */
		std::vector<std::pair<std::string, std::string>>
			*m_staticData;

};

/**
 * The OMFData class.
 * A reading is formatted with OMF specifications
 */
class OMFData
{
	public:
		OMFData(const Reading& reading, const long typeId);
		const std::string& OMFdataVal() const;
	private:
		std::string	m_value;
};

#endif
