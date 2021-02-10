# -*- coding: utf-8 -*-

# FLEDGE_BEGIN
# See: http://fledge-iot.readthedocs.io/
# FLEDGE_END

""" Common code to the north facing plugins

"""

import asyncio

from fledge.common.configuration_manager import ConfigurationManager


# Messages used for Information, Warning and Error notice
MESSAGES_LIST = {

    # Information messages
    "i000000": "information.",

    # Warning / Error messages
    "e000000": "general error.",

    "e000001": "ERROR - the plugin cannot be executed directly.",

    "e000010": "cannot complete the retrieval of the plugin information - error details |{0}|",
    "e000011": "cannot initialize the plugin - error details |{0}|",
    "e000012": "cannot initialize the logger - error details |{0}|",
    "e000013": "cannot complete the termination of the plugin - error details |{0}|",

    "e000020": "cannot retrieve information about the sensor.",
    "e000021": "cannot complete the preparation of the in memory structure.",
    "e000022": "unable to extend the memory structure with new data.",
    "e000023": "cannot prepare sensor information for the destination - error details |{0}|",
    "e000024": "an error occurred during the request to the destination - server address |{0}| - error details |{1}|",

    "e000030": "cannot update the reached position.",
    "e000031": "cannot complete the sending operation - error details |{0}|",
    "e000032": "an error occurred during the request to the destination, the error is considered not blocking "
               "- status code |{0}| - error details |{1}|",
}


def convert_to_type(value):
    """Evaluates and converts to the type in relation to its actual value, for example "180.2" to float 180.2

     Args:
        value : value to evaluate and convert
     Returns:
         value_converted: converted value
     Raises:
     """

    value_type = evaluate_type(value)

    if value_type == "string":
        value_converted = value

    elif value_type == "number":
        value_converted = float(value)

    elif value_type == "integer":
        value_converted = int(value)
    else:
        value_converted = value

    return value_converted


def evaluate_type(value):
    """Evaluates the type in relation to its value

     Args:
        value : value to evaluate
     Returns:
         Evaluated type {integer,number,string}
     Raises:
     """

    if isinstance(value, list):
        evaluated_type = "array"
    elif isinstance(value, dict):
        evaluated_type = "string"
    else:
        try:
            float(value)

            try:
                # Evaluates if it is a int or a number
                if str(int(float(value))) == str(value):

                    # Checks the case having .0 as 967.0
                    int_str = str(int(float(value)))
                    value_str = str(value)

                    if int_str == value_str:
                        evaluated_type = "integer"
                    else:
                        evaluated_type = "number"

                else:
                    evaluated_type = "number"

            except ValueError:
                evaluated_type = "string"

        except ValueError:
            evaluated_type = "string"

    return evaluated_type


def identify_unique_asset_codes(raw_data):
    """Identify unique asset codes in the data block

    Args:
        raw_data : data block retrieved from the Storage layer that should be evaluated
    Returns:
        unique_asset_codes : list of unique codes

    Raises:
    """

    unique_asset_codes = []

    for row in raw_data:
        asset_code = row['asset_code']
        asset_data = row['reading']

        # Evaluates if the asset_code is already in the list
        if not any(item["asset_code"] == asset_code for item in unique_asset_codes):

            unique_asset_codes.append(
                {
                    "asset_code": asset_code,
                    "asset_data": asset_data
                }
            )

    return unique_asset_codes


def retrieve_configuration(_storage, _category_name, _default, _category_description):
    """Retrieves the configuration from the Category Manager for a category name

     Args:
         _storage: Reference to the Storage Client to be used
         _category_name: Category name to be retrieved
         _default: default values for the category
         _category_description: category description
     Returns:
         _config_from_manager: Retrieved configuration as a Dictionary
     Raises:
     """

    _event_loop = asyncio.get_event_loop()

    cfg_manager = ConfigurationManager(_storage)

    _event_loop.run_until_complete(cfg_manager.create_category(_category_name, _default, _category_description))

    _config_from_manager = _event_loop.run_until_complete(cfg_manager.get_category_all_items(_category_name))

    return _config_from_manager
