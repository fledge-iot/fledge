#ifndef _ACL_H
#define _ACL_H

/*
 * Fledge ACL management
 *
 * Copyright (c) 2022 Dianomic Systems
 *
 * Released under the Apache 2.0 Licence
 *
 * Author: Massimiliano Pinto
 */

#include <string>
#include <vector>

/**
 * This class represents the ACL (Access Control List)
 * as JSON object fetched from Fledge Storage
 *
 * There are utility methods along with ACLReason class for changes handking
 */
class ACL {
	public:
		ACL(const std::string &json);
		const std::string&
			getName() { return m_name; };

	protected:
		class KeyValueItem {
			public:
				KeyValueItem(const std::string& key,
					const std::string& value) :
					m_key(key), m_value(value) {};

			private:
				std::string	m_key;
				std::string	m_value;
		};
		class UrlItem {
			public:
				UrlItem(const std::string& url,
					const std::vector<KeyValueItem>& acl) :
					m_url(url), m_acl(acl) {};

			private:
				std::string	m_url;
				std::vector<KeyValueItem>
						m_acl;
		};

	public:
		const std::vector<KeyValueItem>&
		       getService() { return m_service; };	       
		const std::vector<UrlItem>&
			getURL() { return m_url; };	       
	private:
		std::string	m_name;
		std::vector<KeyValueItem>
				m_service;
		std::vector<UrlItem>
				m_url;

	public:
		/**
		 * This class represents the ACL security change request
		 *
		 * Parsed JSON should have string attributes 'reason' and 'argument'
		 */
		class ACLReason {
			public:
				ACLReason(const std::string &reason);
				const std::string&
					getReason() { return m_reason; };
				const std::string&
					getArgument() { return m_argument; };
			private:
				std::string m_reason;
				std::string m_argument;
		};
};


/**
 * Custom exception ACLMalformed
 */
class ACLMalformed : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "ACL JSON is malformed";
		}
};

/**
 * Custom exception ACLReasonMalformed
 */
class ACLReasonMalformed : public std::exception {
	public:
		virtual const char *what() const throw()
		{
			return "ACL Reason JSON is malformed";
		}
};

#endif
