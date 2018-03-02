#!/usr/bin/env python3

import polyinterface
import sys
from onewire import Onewire

LOGGER = polyinterface.LOGGER


DS18x20_PRECISION = ['temperature9', 'temperature10', 'temperature11', 'temperature12']

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
            self.precision = int(self.polyConfig['customParams']['precision'])
            if self.precision > 3:
                self.precision = 3
            elif self.precision < 0:
                self.precision = 0
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
            family = dev.family
            if not address in self.nodes:
                if family in ['10', '28']:
                    self.addNode(OWTempSensor(self, self.address, address, name, dev))
                elif family == '26':
                    self.addNode(OWTempHumSensor(self, self.address, address, name, dev))
                elif family == '1D':
                    self.addNode(OWCounter(self, self.address, address, name, dev))
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
        LOGGER.debug('Starting {}, using {}'.format(self.device.id, DS18x20_PRECISION[self.controller.precision]))
        self.updateInfo()

    def updateInfo(self):
        temperature_c = self.device.read_float(DS18x20_PRECISION[self.controller.precision])
        temperature_f = (temperature_c * 9 / 5) + 32
        self.setDriver('ST', temperature_c)
        self.setDriver('CLITEMP', temperature_f)

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


class OWTempHumSensor(polyinterface.Node):
    def __init__(self, controller, primary, address, name, device):
        super().__init__(controller, primary, address, name)
        self.device = device

    def start(self):
        self.updateInfo()

    def updateInfo(self):
        temperature_c = self.device.read_float('temperature')
        temperature_f = (temperature_c * 9 / 5) + 32
        if 'HIH4000/humidity' in self.device.attrs:
            humidity = self.device.read_float('HIH4000/humidity')
        else:
            humidity = self.device.read_float('humidity')
        self.setDriver('ST', temperature_c)
        self.setDriver('CLITEMP', temperature_f)
        self.setDriver('CLIHUM', humidity)

    def query(self):
        self.updateInfo()
        self.reportDrivers()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 4},
               {'driver': 'CLITEMP', 'value': 0, 'uom': 17},
               {'driver': 'CLIHUM', 'value': 0, 'uom': 22}
              ]

    id = 'OWTEMPH'

    commands = {
                    'QUERY': query
               }


class OWCounter(polyinterface.Node):
    def __init__(self, controller, primary, address, name, device):
        super().__init__(controller, primary, address, name)
        self.device = device

    def start(self):
        self.updateInfo()

    def updateInfo(self):
        counterA = self.device.read_int('counters.A')
        counterB = self.device.read_int('counters.B')
        self.setDriver('ST', counterA)
        self.setDriver('GV0', counterB)

    def query(self):
        self.updateInfo()
        self.reportDrivers()

    drivers = [{'driver': 'ST', 'value': 0, 'uom': 110},
               {'driver': 'GV0', 'value': 0, 'uom': 110}
              ]

    id = 'OWCOUNT'

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
