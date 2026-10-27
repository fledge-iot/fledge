#include <gtest/gtest.h>
#include <reading.h>
#include <omf.h>
#include <http_sender.h>
#include <deque>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

using namespace std;

namespace
{

struct Reply
{
	enum Kind { Status, ThrowConflict, ThrowError };
	Kind kind;
	string body;
};

string omfErrorBody(int code, const string& message)
{
	return "{\"Messages\":[{\"Status\":{\"Code\":" + to_string(code) + "},"
		"\"Events\":[{\"Severity\":\"Error\",\"EventInfo\":{\"Message\":\"" + message + "\"}}]}]}";
}

class ScriptedSender : public HttpSender
{
	public:
		void script(const string& messageType, Reply::Kind kind, const string& body)
		{
			m_script[messageType].push_back({kind, body});
		}

		int count(const string& messageType) const
		{
			int n = 0;
			for (const string& call : m_calls)
			{
				if (call == messageType)
				{
					n++;
				}
			}
			return n;
		}

		size_t calls() const { return m_calls.size(); }
		void clearCalls() { m_calls.clear(); }

		int sendRequest(const string& method, const string& path,
				const vector<pair<string, string>>& headers,
				const string& payload) override
		{
			string type;
			for (const pair<string, string>& header : headers)
			{
				if (header.first == "messagetype")
				{
					type = header.second;
				}
			}
			m_calls.push_back(type);
			m_response.clear();

			deque<Reply>& queue = m_script[type];
			if (queue.empty())
			{
				return type == "Data" ? 202 : 200;
			}
			Reply reply = queue.front();
			queue.pop_front();
			m_response = reply.body;
			if (reply.kind == Reply::ThrowConflict)
			{
				throw Conflict(reply.body);
			}
			if (reply.kind == Reply::ThrowError)
			{
				throw runtime_error("scripted failure");
			}
			return 200;
		}

		void setProxy(const string&) override {}
		string getHostPort() override { return "pi.test:443"; }
		string getHTTPResponse() override { return m_response; }
		unsigned int getMaxRetries() override { return 0; }
		void setAuthMethod(string&) override {}
		void setAuthBasicCredentials(string&) override {}
		void setMaxRetries(unsigned int) override {}
		void setOCSNamespace(string&) override {}
		void setOCSTenantId(string&) override {}
		void setOCSClientId(string&) override {}
		void setOCSClientSecret(string&) override {}
		void setOCSToken(string&) override {}

	private:
		map<string, deque<Reply>> m_script;
		vector<string> m_calls;
		string m_response;
};

class OmfRecovery : public ::testing::Test
{
	protected:
		OmfRecovery() : omf("recovery", sender, "/omf", types, "token")
		{
			omf.setPIServerEndpoint(ENDPOINT_PIWEB_API);
			omf.setNamingScheme(NAMINGSCHEME_CONCISE);
			omf.setSendFullStructure(false);
			omf.setDelimiter(".");
			omf.setDataActionCode("update");
			omf.setStaticData(&staticData);
			omf.setDefaultAFLocation("/Fledge");
			omf.setResendDelays(0, 0);
			DatapointValue value(1.5);
			readings.push_back(new Reading("asset1", new Datapoint("value", value)));
		}

		~OmfRecovery()
		{
			for (Reading *reading : readings)
			{
				delete reading;
			}
		}

		uint32_t send() { return omf.sendToServer(readings, false, false); }

		ScriptedSender sender;
		map<string, OMFDataTypes> types;
		vector<pair<string, string>> staticData;
		vector<Reading *> readings;
		OMF omf;
};

}

TEST_F(OmfRecovery, DataConflictIsRetriedAndResendsTypesAndContainers)
{
	sender.script("Data", Reply::ThrowConflict,
		omfErrorBody(409, "An error processing the OMF data message occurred"));

	EXPECT_EQ(0u, send());
	EXPECT_TRUE(omf.isPIstable());
	EXPECT_EQ(1, sender.count("Container"));

	sender.clearCalls();

	EXPECT_EQ(readings.size(), send());
	EXPECT_TRUE(omf.isPIstable());
	EXPECT_GE(sender.count("Type"), 1);
	EXPECT_EQ(1, sender.count("Container"));
	EXPECT_EQ(1, sender.count("Data"));
}

TEST_F(OmfRecovery, ContainerNotFoundIsRetriedAndResendsTypesAndContainers)
{
	sender.script("Data", Reply::ThrowError, omfErrorBody(404, "Container not found."));

	EXPECT_EQ(0u, send());
	EXPECT_TRUE(omf.isPIstable());

	sender.clearCalls();

	EXPECT_EQ(readings.size(), send());
	EXPECT_TRUE(omf.isPIstable());
	EXPECT_GE(sender.count("Type"), 1);
	EXPECT_EQ(1, sender.count("Container"));
	EXPECT_EQ(1, sender.count("Data"));
}

TEST_F(OmfRecovery, ContainerFlushConflictStillStopsProcessing)
{
	sender.script("Container", Reply::ThrowConflict,
		omfErrorBody(409, "A container with the supplied ID already exists, but does not match the supplied container."));

	EXPECT_EQ(0u, send());
	EXPECT_FALSE(omf.isPIstable());
	EXPECT_EQ(0, sender.count("Data"));
}

TEST_F(OmfRecovery, NothingIsSentWhileTheBackOffIsPending)
{
	omf.setResendDelays(3600, 3600);
	sender.script("Data", Reply::ThrowConflict,
		omfErrorBody(409, "An error processing the OMF data message occurred"));

	EXPECT_EQ(0u, send());

	sender.clearCalls();

	EXPECT_EQ(0u, send());
	EXPECT_EQ(0u, sender.calls());
}
