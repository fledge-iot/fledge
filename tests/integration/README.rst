*************************
FogLAMP Integration Tests
*************************

Integration tests are the second category of test in FogLAMP. These test ensures that two or more FogLAMP units when
integrated works good as a single component.

For example, testing of purge process. To purge any data in FogLAMP, it is required that we have asset data in FogLAMP
database. Other scenarios can be that we want to test the purge process with different set of configurations. This
requires integration of different components like Storage, configuration manager and purge task to work as
component that we are interested to test.
This kind of testing requires that all the different units work as a single sub-system.

Since these kinds of tests interacts between two or more heterogeneous systems, these are often slow in nature.
