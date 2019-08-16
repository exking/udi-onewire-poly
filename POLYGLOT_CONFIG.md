# UDI Polyglot v2 OneWire Poly

[![license](https://img.shields.io/github/license/mashape/apistatus.svg)](https://github.com/exking/udi-onewire-poly/blob/master/LICENSE)

Optional configuration:
 - `ow_conn` - connection information for the owserver (default: "localhost:4304")
 - `precision` - how many decimal digits to read 0..3 (default: "1")
 - `logfile` - filename (full path) to write a log file to, if specified
 - Optionally you can use sensor id as a parameter to specify a correction value, for example if sensor "FF0B0BB31111" is 5 degrees Celsius ahead - specify "FF0B0BB31111" as a key and "-5" as a value.
