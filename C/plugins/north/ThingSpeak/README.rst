***********************
ThingSpeak North Plugin
***********************

This is a FogLAMP north plugin for talking to the MathWorks ThingSpeak
web API. This allows buffered reading to be sent to the ThingSpeak API
and further analysed in MATLAB. https://thingspeak.com

Building
========

To make ThingSpeak plugin run the commands:
::
  mkdir build
  cd build
  cmake ..
  make

Configuration
=============

API
  The address of the ThingSPeak web API, this can usually be left to
  the default value.

channelId
  Every ThingSpeak channel has a channel ID that is allocated when
  the channel is created. This configuration option should contain the
  channel ID allocated in ThingSpeak.

write_api_kwy
  The write API key allocated to this channel.

fields
  The set of asset readings that correspond to the fields in the
  channel. Up to 8 fields may be defined per channel, the fields JSON
  document lists those assets and readings within the assets for each of
  the fields. This JSON document consists of an order array of objects,
  each with an asset and a reading property. These will be sent to
  ThingSpeak with the first array entry mapping to field1, the second
  to field 2 etc.

For example, to send the readings "temperature" and "humidity" for the
asset "station1" to ThingSpeak, the fields configuration object would
appear as follows

::
  {
      "elements" : [
                     {
                        "asset"   : "station1",
                        "reading" : "temperature"
                     },
                     {
                        "asset"   : "station1",
                        "reading" : "humidity"
                     }
                   ]
  }
