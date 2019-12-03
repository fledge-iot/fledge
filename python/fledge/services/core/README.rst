*************************
Fledge Core Microservice
*************************

This directory contians the elements of the core microservice within
Fledge. The core is the first microservice started and contians services
used by other microservices in Fledge, the REST API to the external
world and the orchestrtion and central management fucntions of Fledge.

Code in this directory and sub-directories of this directory are used
exclusively in the core and not shaed with any other microservices.

Starting the Service
====================

Use ``python -m fledge.services.core`` to start the microservice as
a regular process. Alternatively, use the *fledge* script in the 
*scripts* development directory and in the *bin* deployment directory
to start the core. The command is ``fledge start``.

