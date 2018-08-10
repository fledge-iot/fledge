***********************
ThingSpeak North Plugin
***********************

This is a FogLAMP north plugin for talkgn to the MathWorks ThingsSpeak
web API. This allows buffered reading to be sent to the ThingSpeak API
and further analysed in MATLAB.

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
  The address of the ThingSPeak web API, this can usually be left to the default value.

channelId
  Every ThingSpeak channel has a channel ID that is allocated when the channel is created. This configuration option should contain the channel ID allocated in ThingSpeak.

write_api_kwy
  The write API key allocated to this channel.

fields
  The set of asset readings that correspond tp the fields in the channel. Up to 8 fields may be defined per channel, the fields JSON document lists those assets and reaings within the assets for each of the fields.
