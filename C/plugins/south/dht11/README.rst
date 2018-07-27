=========================================
DHT11 C/C++ South plugin for Raspberry Pi
=========================================

The DHT11 C/C++ module uses libwiringPi. To install that:

.. code-block:: console

        git clone git://git.drogon.net/wiringPi

        cd wiringPi

        ./build 

The wiringPi library and related symbolic link would get installed in /usr/local/lib.

DHT11 schedule has been added in disabled mode in sqlite init.sql.

To enable the dht11 plugin schedule:

.. code-block:: console

        curl -sX PUT http://10.2.5.15:8081/foglamp/schedule/6b25f4d9-c7f3-4fc8-bd4a-4cf79f7055ca/enable

