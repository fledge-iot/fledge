Debugger Command Line Test Programs
===================================

This directory contains a set of utilities used to manually test the pipeline debugger features. These tests should be run against a live system built from this branch.

To start testing;

  - Change directory to the debugger directory

  - Type the command

    .. code-block:: console

        ./debug <ServiceName>

    Where *<ServiceName>* is the name of a south or north service. You will need to quote the name if it contains whitespace or wildcard characters that have meaning to the shell.

   - Attach the debugger to the pipeline by using the attach command

     .. code-block:: console

         attach

The debugger is now attached to the pipeline and collecting one reading at each point in the pipeline.

To see the list of commands available type the *commands* command

.. code-block:: console

    % commands
    attach:		Attach the pipeline debugger
    buffer:		Return the contents of the buffers at every pipeline element
    detach:		Detach the debugger from the pipeline
    isolate:	Isolate the pipeline from the destination
    replay:		Replay the buffered data through the pipeline
    resumeIngest:	Resume the flow of data into the pipeline
    setBuffer:	Set the number of readings to hold in each buffer, passing an integer argument
    state:		Return the state of the debugger
    step:		Allow readings to flow into the pipeline. Pass an optional number of readings to ingest; default to 1 if omitted
    store:		Allow data to flow out of the pipeline into storage
    suspendIngest:	Suspend the ingestion of data into the pipeline

The data output from the *buffer* command shows the readings at the input to the named filter in the pipeline. The item name *Writer* is the end of the pipeline that writes data to storage, in south plugins. The item named *Branch* is a branch point in the pipeline.

To exit the debugger simple type exit or <Control>-D
