/*
 * Fledge RapaidJSON JSONPath search helper
 *
 * Copyright (c) 2020 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Mark Riddoch
 */
#include <JSONPath.h>
#include <logger.h>
#include <cstring>
#include <stdexcept>

using namespace std;
using namespace rapidjson;

JSONPath::JSONPath(const string& path) : m_path(path)
{
	m_logger = Logger::getLogger();
}

/**
 * Destructor for the JSONPath
 *
 * Reclaim the vector of components.
 */
JSONPath::~JSONPath()
{
}

/**
 * Find the matching node in the JSON document
 *
 * param node	The node to search from
 * @return the matching node. Throws an exception if there was no match
 */

Value *JSONPath::findNode(Value& root)
{
	if (m_parsed.size() == 0)
	{
		parse();
	}

	Value *node = &root;

	for (int i = 0; i < m_parsed.size(); i++)
	{
		node = m_parsed[i]->match(node);
	}
	return node;
}

/**
 * Parse the m_path JSON path. Throws an exception if there
 * was a parse error.
 *
 * The supported elements are
 * 	Literal object name		/a
 * 	Array Index			a[1]
 * 	Array with matching predicate	a[name==value]
 */
void JSONPath::parse()
{
char *path, *ptr, *sp;

	path = strdup(m_path.c_str());
	ptr = strtok_r(path, "/", &sp);
	while (ptr)
	{
		char *p = ptr;
		char *bstart = NULL, *bend = NULL, *bequal = NULL;
		while (*p)
		{
			if (*p == '[')
			{
				bstart = p + 1;
			}
			if (*p == ']')
			{
				bend = p - 1;
			}
			if (*p == '=' && *(p+1) == '=')
			{
				bequal = p;
			}
			p++;
		}
		if (bstart == NULL && bend == NULL && bequal == NULL)
		{
			string s(ptr);
			m_parsed.push_back(new LiteralPathComponent(s));
		}
		if (bstart != NULL && bend != NULL)
		{
			if (bstart > bend)
			{
				m_logger->error("Invalid JSONPath '%s', malformed selector", path);
				goto done;
			}
			*(bstart - 1) = 0;
			string name(ptr);
			if (bequal == NULL)
			{
				char *eptr;
				long index = strtol(bstart, &eptr, 10);
				if (eptr != bend + 1)
				{
					m_logger->error("Invalid JSONPath '%s', expected numeric selector");
					goto done;
				}
				m_parsed.push_back(new IndexPathComponent(name, index));
			}
			else
			{
				char *property = bstart;
				char *value = bequal + 2;
				*(bend + 1) = 0;
				*bequal = 0;
				string p(property), v(value);
				m_parsed.push_back(new MatchPathComponent(name, p, v));
			}
		}


		ptr = strtok_r(NULL, "/", &sp);
	}
done:
	free(path);
}

/**
 * A match against a literal path component
 */
JSONPath::LiteralPathComponent::LiteralPathComponent(string& name) : m_name(name)
{
}

/**
 * Return the child object of node that matchs the literal name given
 *
 * @param node	The node to match
 * @return pointer to the matching node
 */
rapidjson::Value *JSONPath::LiteralPathComponent::match(rapidjson::Value *node)
{
	if (node->IsObject() && node->HasMember(m_name.c_str()))
	{
		return &((*node)[m_name.c_str()]);
	}
	throw runtime_error("Document has no member " + m_name);
}

/**
 * A match against an array index
 */
JSONPath::IndexPathComponent::IndexPathComponent(string& name, int index) : m_name(name), m_index(index)
{
}

/**
 * Return the object at the index position of the specified array
 *
 * @param node	The node to match
 * @return pointer to the matching node
 */
rapidjson::Value *JSONPath::IndexPathComponent::match(rapidjson::Value *node)
{
	if (node->IsObject() && node->HasMember(m_name.c_str()))
	{
		Value& n  = (*node)[m_name.c_str()];
		if (n.IsArray())
		{
			return &n[m_index];
		}
	}
	throw runtime_error("Document has no member " + m_name + " or it is not an array");
}

/**
 * Amatch against an object that hase a particular name/value pair
 */
JSONPath::MatchPathComponent::MatchPathComponent(string& name, string& property, string& value) : m_name(name), m_property(property), m_value(value)
{
}

/**
 * Match a node within an array or object
 *
 * @param node	The node to match
 * @return pointer to the matching node
 */
rapidjson::Value *JSONPath::MatchPathComponent::match(rapidjson::Value *node)
{
	if (node->IsObject() && node->HasMember(m_name.c_str()))
	{
		Value& n  = (*node)[m_name.c_str()];
		if (n.IsArray())
		{
			for (auto& v : n.GetArray())
			{
				if (v.IsObject())
				{
					if (v.HasMember(m_property.c_str()))
					{
						if (v[m_property.c_str()].IsString() 
								&& m_value.compare(v[m_property.c_str()].GetString()) == 0)
							return &v;
						if (v[m_property.c_str()].IsInt())
						{
							long val = v[m_property.c_str()].GetInt();
							long tval = strtol(m_value.c_str(), NULL, 10);
							if (val == tval)
								return &v;
						}
						else if (v[m_property.c_str()].IsDouble())
						{
							double val = v[m_property.c_str()].GetDouble();
							double tval = strtod(m_value.c_str(), NULL);
							if (val == tval)
								return &v;
						}
						else if (v[m_property.c_str()].IsBool())
						{
							bool val = v[m_property.c_str()].GetBool();
							if (val && (m_value.compare("true") == 0 || m_value.compare("TRUE") == 0))
								return &v;
							if (val == false && (m_value.compare("false") == 0 || m_value.compare("FALSE") == 0))
								return &v;
						}
					}
				}
			}
		}
	}
	throw runtime_error(string("Document has no member ") + m_name + string(" or it does not have a ") + m_property + " property");
}
