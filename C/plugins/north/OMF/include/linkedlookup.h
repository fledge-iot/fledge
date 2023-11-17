#ifndef _LINKEDLOOKUP_H
#define _LINKEDLOOKUP_H
typedef enum {
	OMFBT_UNKNOWN, OMFBT_DOUBLE64, OMFBT_DOUBLE32, OMFBT_INTEGER16,
	OMFBT_INTEGER32, OMFBT_INTEGER64, OMFBT_UINTEGER16, OMFBT_UINTEGER32,
	OMFBT_UINTEGER64, OMFBT_STRING, OMFBT_FLEDGEASSET
} OMFBaseType;

/**
 * Lookup status bit
 */
#define	LAL_ASSET_SENT		0x01	// We have sent the asset 
#define LAL_LINK_SENT		0x02	// We have sent the link to the base type
#define LAL_CONTAINER_SENT	0x04	// We have sent the container
#define LAL_AFLINK_SENT		0x08	// We have sent the link to the AF location

/**
 * Linked Asset Information class
 *
 * This is the data stored for each asset and asset datapoint pair that
 * is being sent to PI using the linked container mechanism. We use the class
 * so we can combine all the information we need in a single lookup table,
 * this not only saves space but allows to build and retain the table
 * before we start building the payloads. This hopefully will help prevent
 * to much memory fragmentation, which was an issue with the old, separate
 * lookup mechanism we had.
 */
class LALookup {
	public:
		LALookup()	{ m_sentState = 0; m_baseType = OMFBT_UNKNOWN; };
		bool		assetState() { return (m_sentState & LAL_ASSET_SENT) != 0; };
		bool		linkState() { return (m_sentState & LAL_LINK_SENT) != 0; };
		bool		containerState() { return (m_sentState & LAL_CONTAINER_SENT) != 0; };
		bool		afLinkState() { return (m_sentState & LAL_AFLINK_SENT) != 0; };
		void		setBaseType(const std::string& baseType);
		OMFBaseType	getBaseType() { return m_baseType; };
		std::string	getBaseTypeString();
		void		assetSent() { m_sentState |= LAL_ASSET_SENT; };
		void		linkSent() { m_sentState |= LAL_LINK_SENT; };
		void		afLinkSent() {  m_sentState |= LAL_AFLINK_SENT; };
		void		containerSent(const std::string& baseType);
		void		containerSent(OMFBaseType baseType) { m_baseType = baseType; };
	private:
		uint8_t		m_sentState;
		OMFBaseType	m_baseType;
};
#endif
