#!/bin/bash

# Reads configuration setting
source ${SUITE_BASEDIR}/suite.cfg

#
# Main
#
url_databases=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k https://${PI_SERVER}/piwebapi/assetservers | jq --raw-output '.Items | .[] | .Links | .Databases '`
echo url_databases :${url_databases}: > /dev/tty

#
url_elements=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k ${url_databases} |  jq --raw-output '.Items | .[] | select(.Name=="'${PI_SERVER_DATABASE}'") | .Links | .Elements'`
echo url_elements :${url_elements}: > /dev/tty

#
url_elements_list=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k ${url_elements} |  jq --raw-output '.Items | .[] | .Links | .Elements'`
echo url_elements_list :${url_elements_list}: > /dev/tty

#
web_id=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k ${url_elements_list} |  jq --raw-output '.Items | .[] | select(.Name=="'${OMF_PRODUCER_TOKEN}'") | .WebId '`
echo web_id :${web_id}: > /dev/tty

#
# Deletes AF hierarchy
#
if [[ ${web_id} != "" ]]; then

    curl -u ${PI_SERVER_UID}:${PI_SERVER_PWD} -X DELETE -k https://${PI_SERVER}/piwebapi/elements/${web_id}
fi

#
# Deletes AF ElementTemplates (type definition)
#
url_element_templates=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k ${url_databases} |  jq --raw-output '.Items | .[] | select(.Name=="'${PI_SERVER_DATABASE}'") | .Links | .ElementTemplates'`
echo url_elementTemplates :${url_element_templates}: > /dev/tty

web_id=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k ${url_element_templates} |  jq --raw-output '.Items | .[] | select(.Name | contains("'${OMF_TYPE_ID}_${ASSET_CODE}'")) | .WebId '`
echo web_id :${web_id}: > /dev/tty


if [[ ${web_id} != "" ]]; then

    curl -u ${PI_SERVER_UID}:${PI_SERVER_PWD} -X DELETE -k https://${PI_SERVER}/piwebapi/elementtemplates/${web_id}
fi


#
# Deletes PI server data
#
url_points=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k https://${PI_SERVER}/piwebapi/dataservers | jq --raw-output '.Items | .[] | .Links | .Points '`
echo url_points :${url_points}: > /dev/tty

web_id=`curl -s -u  ${PI_SERVER_UID}:${PI_SERVER_PWD} -X GET -k ${url_points} |  jq --raw-output '.Items | .[] | select(.Name | contains("'${OMF_PRODUCER_TOKEN}'")) | .WebId '`
echo web_id :${web_id}: > /dev/tty

if [[ ${web_id} != "" ]]; then

    curl -u ${PI_SERVER_UID}:${PI_SERVER_PWD} -X DELETE -k https://${PI_SERVER}/piwebapi/points/${web_id}
fi
