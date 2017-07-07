#!/usr/bin/env python3

import asyncio
from foglamp.admin_api import controller as admin_api_controller
 
 
def start():
    """Starts the service"""
    admin_api_controller.start()
    asyncio.get_event_loop().run_forever()


if __name__ == "__main__":
    start()

