*************************
FogLAMP Core Microservice
*************************

This directory contians the elements of the core microservice within
FogLAMP. The core is the first microservice started and contians services
used by other microservices in FogLAMP, the REST API to the external
world and the orchestrtion and central management fucntions of FogLAMP.

Code in this directory and sub-directories of this directory are used
exclusively in the core and not shaed with any other microservices.

Starting the Service
====================

Use ``python -m foglamp.services.core`` to start the microservice as
a regular process. Alternatively, use the *foglamp* script in the 
*scripts* development directory and in the *bin* deployment directory
to start the core. The command is ``foglamp start``.

