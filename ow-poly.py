#!/usr/bin/env python3

import polyinterface
import sys
import logging
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
        self.datalogger = None
        self.on = False
        self.sensor_count = 0

    def start(self):
        LOGGER.setLevel(logging.INFO)
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
        if 'logfile' in self.polyConfig['customParams']:
            file_handler = logging.handlers.TimedRotatingFileHandler(self.polyConfig['customParams']['logfile'], when="midnight", backupCount=5)
            formatter = logging.Formatter('%(asctime)s,%(message)s','%Y-%m-%d,%H:%M:%S')
            file_handler.setFormatter(formatter)
            self.datalogger = logging.getLogger('csvlog')
            self.datalogger.setLevel(logging.DEBUG)
            self.datalogger.addHandler(file_handler)
        try:
            self.ow = Onewire(ow_conn)
        except Exception as ex:
            LOGGER.error('OneWire Initialization Exception: {}'.format(ex))
        else:
            self.discover()
            self.setDriver('GPV', self.sensor_count)

    def stop(self):
        LOGGER.info('OneWire is stopping')

    def shortPoll(self):
        for node in self.nodes:
            self.nodes[node].updateInfo()
        if self.on:
            self.reportCmd('DOF')
            self.on = False
        else:
            self.reportCmd('DON')
            self.on = True
            
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
                self.sensor_count += 1
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
    drivers = [{'driver': 'ST', 'value': 1, 'uom': 2},
               {'driver': 'GPV', 'value': 0, 'uom': 108}]


class OWTempSensor(polyinterface.Node):
    def __init__(self, controller, primary, address, name, device):
        super().__init__(controller, primary, address, name)
        self.device = device
        self.temp_correction = 0
        self.temp_attribute = 'temperature'

    def start(self):
        self.temp_attribute = DS18x20_PRECISION[self.controller.precision]
        LOGGER.info(f'Starting {self.device.id}, using {self.temp_attribute}')
        if self.device.id in self.controller.polyConfig['customParams']:
            try:
                self.temp_correction = float(self.controller.polyConfig['customParams'][self.device.id])
            except Exception as ex:
                LOGGER.error(f'Device {self.device.id} correction value invalid: {ex}')
            else:
                LOGGER.info(f'Will apply {self.temp_correction} correction to {self.device.id}')
        try:
            temperature_c = self.device.read_float(self.temp_attribute) + self.temp_correction
        except AttributeError:
            LOGGER.info(f'Failed to read {self.temp_attribute} of {self.device.id}, fallback to "temperature"')
            self.temp_attribute = 'temperature'
        except Exception as ex:
            LOGGER.error(f'Failed to read: {self.device.id}: {ex}')
        self.updateInfo()

    def updateInfo(self):
        try:
            temperature_c = self.device.read_float(self.temp_attribute) + self.temp_correction
        except Exception as ex:
            LOGGER.error(f"Failed to read: {self.device.id}: {ex}")
            return False
        temperature_f = (temperature_c * 9 / 5) + 32
        self.setDriver('ST', temperature_c)
        self.setDriver('CLITEMP', round(temperature_f, 4))
        if self.controller.datalogger is not None:
            self.controller.datalogger.debug(f'{self.device.id},{temperature_c},{temperature_f}')

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
        self.temp_correction = 0

    def start(self):
        LOGGER.info('Starting {}'.format(self.device.id))
        if self.device.id in self.controller.polyConfig['customParams']:
            try:
                self.temp_correction = float(self.controller.polyConfig['customParams'][self.device.id])
            except Exception as ex:
                LOGGER.error('Device {} correction value invalid: {}'.format(self.device.id, ex))
            else:
                LOGGER.info('Will apply {} temperature correction to {}'.format(self.temp_correction, self.device.id))
        self.updateInfo()

    def updateInfo(self):
        try:
            temperature_c = self.device.read_float('temperature') + self.temp_correction
        except Exception as ex:
            LOGGER.error("Failed to read: {}".format(self.device.id))
            return False
        temperature_f = (temperature_c * 9 / 5) + 32
        if 'HIH4000/humidity' in self.device.attrs:
            try:
                humidity = self.device.read_float('HIH4000/humidity')
            except Exception as ex:
                LOGGER.error("Failed to read: {}".format(self.device.id))
                return False
        else:
            try:
                humidity = self.device.read_float('humidity')
            except Exception as ex:
                LOGGER.error("Failed to read: {}".format(self.device.id))
                return False
        self.setDriver('ST', temperature_c)
        self.setDriver('CLITEMP', round(temperature_f, 4))
        self.setDriver('CLIHUM', humidity)
        if self.controller.datalogger is not None:
            self.controller.datalogger.debug("{},{},{},{}".format(self.device.id,temperature_c,temperature_f,humidity))

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
        LOGGER.info('Starting {}'.format(self.device.id))
        self.updateInfo()

    def updateInfo(self):
        try:
            counterA = self.device.read_int('counters.A')
            counterB = self.device.read_int('counters.B')
        except Exception as ex:
            LOGGER.error("Failed to read: {}".format(self.device.id))
            return False
        self.setDriver('ST', counterA)
        self.setDriver('GV0', counterB)
        if self.controller.datalogger is not None:
            self.controller.datalogger.debug("{},{},{}".format(self.device.id,counterA,counterB))

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
