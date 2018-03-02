#!/usr/bin/env python3

import polyinterface
import sys
from onewire import Onewire

LOGGER = polyinterface.LOGGER


class Controller(polyinterface.Controller):
    def __init__(self, polyglot):
        super().__init__(polyglot)
        self.name = 'OneWire Controller'
        self.address = 'owctrl'
        self.primary = self.address
        self.ow = None
        self.precision = 1

    def start(self):
        LOGGER.info('Started OneWire controller')
        if 'precision' in self.polyConfig['customParams']:
            self.precision = self.polyConfig['customParams']['precision']
        if 'ow_conn' in self.polyConfig['customParams']:
            ow_conn = self.polyConfig['customParams']['ow_conn']
        else:
            ow_conn = 'localhost:4304'
        try:
            self.ow = Onewire(ow_conn)
        except Exception as ex:
            LOGGER.error('OneWire Initialization Exception: {}'.format(ex))
        else:
            self.discover()

    def stop(self):
        LOGGER.debug('OneWire is stopping')

    def shortPoll(self):
        for node in self.nodes:
            self.nodes[node].updateInfo()
            
    def updateInfo(self):
        pass

    def query(self):
        for node in self.nodes:
            self.nodes[node].reportDrivers()

    def discover(self, command=None):
        for dev in self.ow.find():
            address = dev.path.replace('.','').lower()[:14]
            name = dev.id
            family = int(dev.family)
            if not address in self.nodes:
                if family in [10, 28]:
                    self.addNode(OWTempSensor(self, self.address, address, name, dev))
                else:
                    LOGGER.info('Sensor {} family {} is not yet supported'.format(name, family))

    id = 'OWCTRL'
    commands = {'DISCOVER': discover}
    drivers = [{'driver': 'ST', 'value': 0, 'uom': 2}]


class OWTempSensor(polyinterface.Node):
    def __init__(self, controller, primary, address, name, device):
        super().__init__(controller, primary, address, name)
        self.device = device

    def start(self):
        self.updateInfo()

    def updateInfo(self):
        temperature_c = self.device.read_float('temperature')
        temperature_f = (temperature_c * 9 / 5) + 32
        self.setDriver('ST', round(temperature_c, self.controller.precision))
        self.setDriver('CLITEMP', round(temperature_f, self.controller.precision))

    def query(self):
        self.updateInfo()
        self.reportDrivers()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 4},
               {'driver': 'CLITEMP', 'value': 0, 'uom': 17}
              ]

    id = 'OWTEMP'

    commands = {
                    'QUERY': query
               }


if __name__ == "__main__":
    try:
        polyglot = polyinterface.Interface('OneWire')
        polyglot.start()
        control = Controller(polyglot)
        control.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
