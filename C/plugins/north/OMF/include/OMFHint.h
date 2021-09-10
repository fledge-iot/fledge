#ifndef _OMF_HINT_H
#define _OMF_HINT_H

#include <rapidjson/document.h>

/**
 * Virtual base class for an OMF Hint
 */
class OMFHint
{
	public:
		virtual ~OMFHint() = default;
		const std::string&	getHint() const { return m_hint; };
	protected:
		std::string	m_hint;
};

/**
 * A number hint, defines how number type should be defined, float64 or float32

 */
class OMFNumberHint : public OMFHint
{
	public:
		OMFNumberHint(const std::string& type) { m_hint = type; };
		~OMFNumberHint() {};
};

/**
 * A integer hint, defines how ineteger type should be defined, int64, int32 o int16

 */
class OMFIntegerHint : public OMFHint
{
public:
	OMFIntegerHint(const std::string& type) { m_hint = type; };
	~OMFIntegerHint() {};
};


/**
 * A tag hint, used to define an existing OMF container or tag to use
 */
class OMFTagHint : public OMFHint
{
	public:
		OMFTagHint(const std::string& tag) { m_hint = tag; };
		~OMFTagHint() {};
};

/**
 * A Type name hint, tells us how to name the types we use
 */
class OMFTypeNameHint : public OMFHint
{
	public:
		OMFTypeNameHint(const std::string& name) { m_hint = name; };
		~OMFTypeNameHint() {};
};

/**
 * A tag name hint, tells us whuch tag name ot use in PI
 */
class OMFTagNameHint : public OMFHint
{
	public:
		OMFTagNameHint(const std::string& name) { m_hint = name; };
		~OMFTagNameHint() {};
};


/**
 * A AFLocation hint, tells use in which Asset Framework hierarchy the asset should be created
 */
class OMFAFLocationHint : public OMFHint
{
public:
	OMFAFLocationHint(const std::string& name) { m_hint = name; };
	~OMFAFLocationHint() {};
};

/**
 * A set of hints for a reading
 */
class OMFHints
{
	public:
		OMFHints(const std::string& hints);
		~OMFHints();
		const std::vector<OMFHint *>&
					getHints() const { return m_hints; };
		const std::vector<OMFHint *>&
					getHints(const std::string&) const;
		const unsigned short	getChecksum() { return m_chksum; };
		static string          	getHintForChecksum(const string &hint);
	private:
		rapidjson::Document	m_doc;
		unsigned short		m_chksum;
		std::vector<OMFHint *>	m_hints;
		std::map<std::string, std::vector<OMFHint *> >
					m_datapointHints;
};
#endif
