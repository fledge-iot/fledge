#ifndef _OMF_H
#define _OMF_H
/*
 * Fledge OSI Soft OMF interface to PI Server.
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
#include <rapidjson/document.h>

#define	OMF_HINT	"OMFHint"

#define TYPE_ID_DEFAULT     1
#define FAKE_ASSET_KEY      "_default_start_id_"
#define OMF_TYPE_STRING		"string"
#define OMF_TYPE_INTEGER	"integer"
#define OMF_TYPE_FLOAT		"number"
#define OMF_TYPE_UNSUPPORTED	"unsupported"

enum OMF_ENDPOINT {
	ENDPOINT_PIWEB_API,
	ENDPOINT_CR,
	ENDPOINT_OCS,
	ENDPOINT_EDS
};

enum NAMINGSCHEME_ENDPOINT {
	NAMINGSCHEME_CONCISE,
	NAMINGSCHEME_SUFFIX,
	NAMINGSCHEME_HASH,
	NAMINGSCHEME_COMPATIBILITY
};


using namespace std;
using namespace rapidjson;

std::string ApplyPIServerNamingRules(const std::string &objName, bool *changed);

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
                long           typeId;
                std::string    types;
                unsigned long  typesShort;
				long           namingScheme;
				string         afhHash;
				string         afHierarchy;
				string         afHierarchyOrig;

		unsigned short hintChkSum;
};

class OMFHints;

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

		// Set which PIServer component should be used for the communication
		void setPIServerEndpoint(const OMF_ENDPOINT PIServerEndpoint);

		// Set the naming scheme of the objects in the endpoint
		void setNamingScheme(const NAMINGSCHEME_ENDPOINT namingScheme) {m_NamingScheme = namingScheme;};

		// Generate the container id for the given asset
		std::string generateMeasurementId(const string& assetName);

		// Generate a suffix for the given asset in relation to the selected naming schema and the value of the type id
		std::string generateSuffixType(string &assetName, long typeId);

		// Generate a suffix for the given asset in relation to the selected naming schema and the value of the type id
		long getNamingScheme(const string& assetName);

		string getHashStored(const string& assetName);
		string getPathStored(const string& assetName);
		string getPathOrigStored(const string& assetName);
		bool setPathStored(const string& assetName, string &afHierarchy);
		void deleteAssetAFH(const string& assetName, string& path);
		void createAssetAFH(const string& assetName, string& path);

		// Set the first level of hierarchy in Asset Framework in which the assets will be created, PI Web API only.
		void setDefaultAFLocation(const std::string &DefaultAFLocation);

		bool setAFMap(const std::string &AFMap);

		void setSendFullStructure(const bool sendFullStructure) {m_sendFullStructure = sendFullStructure;};

		void setPrefixAFAsset(const std::string &prefixAFAsset);

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
					std::map<std::string, Reading*>& dataSuperSet);
		// Removed mapped object types found in input data
		void unsetMapObjectTypes(std::map<std::string, Reading*>& dataSuperSet) const;

		void setStaticData(std::vector<std::pair<std::string, std::string>> *staticData)
		{
			m_staticData = staticData;
		};

		void generateAFHierarchyPrefixLevel(string& path, string& prefix, string& AFHierarchyLevel);

		// Retrieve private objects
		map<std::string, std::string> getNamesRules() const { return m_NamesRules; };
		map<std::string, std::string> getMetadataRulesExist() const { return m_MetadataRulesExist; };

		bool getAFMapEmptyNames() const { return m_AFMapEmptyNames; };
		bool getAFMapEmptyMetadata() const { return m_AFMapEmptyMetadata; };

		static std::string ApplyPIServerNamingRulesObj(const std::string &objName, bool *changed);
		static std::string ApplyPIServerNamingRulesPath(const std::string &objName, bool *changed);
		static std::string ApplyPIServerNamingRulesInvalidChars(const std::string &objName, bool *changed);

		static std::string variableValueHandle(const Reading& reading, std::string &AFHierarchy);
		static bool        extractVariable(string &strToHandle, string &variable, string &value, string &defaultValue);

private:
		/**
		 * Builds the HTTP header to send
		 * messagetype header takes the passed type value:
		 * 'Type', 'Container', 'Data'
		 */
		const std::vector<std::pair<std::string, std::string>>
			createMessageHeader(const std::string& type, const std::string& action="create") const;

		// Create data for Type message for current row
		const std::string createTypeData(const Reading& reading, OMFHints *hints);

		// Create data for Container message for current row
		const std::string createContainerData(const Reading& reading, OMFHints *hints);

		// Create data for additional type message, with 'Data' for current row
		const std::string createStaticData(const Reading& reading);

		// Create data Link message, with 'Data', for current row
		std::string createLinkData(const Reading& reading, std::string& AFHierarchyLevel, std::string&  prefix, std::string&  objectPrefix, OMFHints *hints);

		/**
		 * Creata data for readings data content, with 'Data', for one row
		 * The new formatted data have to be added to a new JSON doc to send.
		 * we want to avoid sending of one data row
		 */
		const std::string createMessageData(Reading& reading);

		// Set the the tagName in an assetName Type message
		void setAssetTypeTag(const std::string& assetName,
				     const std::string& tagName,
				     std::string& data);

		void setAssetTypeTagNew(const std::string& assetName,
							 const std::string& tagName,
							 std::string& data);

		// Create the OMF data types if needed
		bool handleDataTypes(const string keyComplete,
			                 const Reading& row,
				             bool skipSendingTypes, OMFHints *hints);

		// Send OMF data types
		bool sendDataTypes(const Reading& row, OMFHints *hints);

		// Get saved dataType
		bool getCreatedTypes(const std::string& keyComplete, const Reading& row, OMFHints *hints);

		// Set saved dataType
		unsigned long calcTypeShort(const Reading& row);


	// Clear data types cache
		void clearCreatedTypes();

		// Increment type-id value
		void incrementTypeId();

                // Handle data type errors
		bool handleTypeErrors(const string& keyComplete, const Reading& reading, OMFHints*hints);

		string errorMessageHandler(const string &msg);

		// Extract assetName from erro message
		std::string getAssetNameFromError(const char* message);

		// Get asset type-id from cached data
		long getAssetTypeId(const std::string& assetName);

		// Increment per asset type-id value
		void incrementAssetTypeId(const std::string& keyComplete);
		void incrementAssetTypeIdOnly(const std::string& keyComplete);

		// Set global type-id as the maximum value of all per asset type-ids
		void setTypeId();

		// Set saved dataType
		bool setCreatedTypes(const Reading& row, OMFHints *hints);

		// Remove cached data types enttry for given asset name
		void clearCreatedTypes(const std::string& keyComplete);

		// Add the 1st level of AF hierarchy if the end point is PI Web API
		void setAFHierarchy();

		bool handleAFHirerarchy();
		bool handleAFHierarchySystemWide();
		bool handleOmfHintHierarchies();

		bool sendAFHierarchy(std::string AFHierarchy);

		bool sendAFHierarchyLevels(std::string parentPath, std::string path, std::string &lastLevel);
		bool sendAFHierarchyTypes(const std::string AFHierarchyLevel, const std::string prefix);
		bool sendAFHierarchyStatic(const std::string AFHierarchyLevel, const std::string prefix);
		bool sendAFHierarchyLink(std::string parent, std::string child, std::string prefixIdParent, std::string prefixId);

		bool manageAFHierarchyLink(std::string parent, std::string child, std::string prefixIdParent, std::string prefixId, std::string childFull, string action);

		bool AFHierarchySendMessage(const std::string& msgType, std::string& jsonData, const std::string& action="create");


		std::string generateUniquePrefixId(const std::string &path);
		void evaluateAFHierarchyRules(const string& assetName, const Reading& reading);
		void retrieveAFHierarchyPrefixAssetName(const string& assetName, string& prefix, string& AFHierarchyLevel);
		void retrieveAFHierarchyFullPrefixAssetName(const string& assetName, string& prefix, string& AFHierarchy);

		bool createAFHierarchyOmfHint(const string& assetName, const  string &OmfHintHierarchy);

		bool HandleAFMapNames(Document& JSon);
		bool HandleAFMapMetedata(Document& JSon);

	private:
		union t_typeCount {
			struct
			{
				unsigned char tTotal;
				unsigned char tFloat;
				unsigned char tString;
				unsigned char spare0;

				unsigned char spare1;
				unsigned char spare2;
				unsigned char spare3;
				unsigned char spare4;
			} cnt;
			unsigned long valueLong = 0;
		};

		std::string	          m_assetName;
		const std::string	  m_path;
		long			      m_typeId;
		const std::string	  m_producerToken;
		OMF_ENDPOINT		  m_PIServerEndpoint;
		NAMINGSCHEME_ENDPOINT m_NamingScheme;
		std::string		      m_DefaultAFLocation;

		bool            m_sendFullStructure;
		// AF hierarchies handling - Metadata MAP
		std::string		m_AFMap;
		bool            m_AFMapEmptyNames;  // true if there are norules to manage
		bool            m_AFMapEmptyMetadata;
		std::string		m_AFHierarchyLevel;
		std::string		m_prefixAFAsset;

		vector<std::string>  m_afhHierarchyAlredyCreated={

			//  Asset Framework path
			// {""}
		};


		map<std::string, std::string>  m_NamesRules={

			// Asset_name   - Asset Framework path
			// {"",         ""}
		};

		map<std::string, std::string>  m_MetadataRulesExist={

			// Property   - Asset Framework path
			// {"",         ""}
		};

		map<std::string, std::string>  m_MetadataRulesNonExist={

			// Property   - Asset Framework path
			// {"",         ""}
		};

		map<std::string, vector<pair<string, string>>>   m_MetadataRulesEqual={

			// Property    - Value  - Asset Framework path
			// {"",         {{"",        ""}} }
		};

		map<std::string, vector<pair<string, string>>>   m_MetadataRulesNotEqual={

			// Property    - Value  - Asset Framework path
			// {"",         {{"",        ""}} }
		};

		map<std::string, vector<pair<string, string>>>  m_AssetNamePrefix ={

			// Property   - Hierarchy - prefix
			// {"",         {{"",        ""}} }
		};

		// Define the OMF format to use for each type
		// the format will not be applied if the string is empty
		std::map<const std::string, std::string> m_formatTypes {
			{OMF_TYPE_STRING, ""},
			{OMF_TYPE_INTEGER,"int64"},
			{OMF_TYPE_FLOAT,  "float64"},
			{OMF_TYPE_UNSUPPORTED,  "unsupported"}
		};

		// Vector with OMF_TYPES
		const std::vector<std::string> omfTypes = { OMF_TYPE_STRING,
							    OMF_TYPE_FLOAT,  // Forces the creation of float also for integer numbers
							    OMF_TYPE_FLOAT,
							    OMF_TYPE_UNSUPPORTED};
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

		// Stores the type for the block of data containing all the used properties
		std::map<string, Reading*> m_SuperSetDataPoints;

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
		OMFData(const Reading& reading,
			string measurementId,
			const OMF_ENDPOINT PIServerEndpoint = ENDPOINT_CR,
			const std::string& DefaultAFLocation = std::string(),
			OMFHints *hints = NULL);

		const std::string& OMFdataVal() const;
	private:
		std::string	m_value;
};

#endif
