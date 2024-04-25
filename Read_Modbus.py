#!/usr/bin/env python3

import pymodbus
from pymodbus.client.tcp import ModbusTcpClient as ModbusClient
from pymodbus.transaction import ModbusRtuFramer as ModbusFramer
import binascii
import datetime
import time

client = ModbusClient(host='192.168.16.254', port=8080, framer=ModbusFramer)
client.connect()

#pymodbus.pymodbus_apply_logging_config(1)

def readRegs(start,regCount=1):
	result = client.read_holding_registers(start,regCount, slave=1)
	return result.registers

def readRegBytes(start,bytecount=1):
	result = client.read_holding_registers(start,(bytecount + 1) >> 1, slave=1)
	buf = bytearray()
	for r in result.registers:
		buf.append((r >> 8) & 0xFF)
		buf.append(r & 0xFF)
	return buf

def loadRegs(startReg,regCount=1):
	regList = list(range(startReg,startReg+regCount))
	regValList = readRegs(regList[0], regCount)
	return dict(zip(regList, regValList))

INVERTER_LIST = [ "Fronius HV", "Goodwe HV/Viessmann HV", "Goodwe LV/Viessmann LV", "KOSTAL HV", "Selectronic LV", "SMA SBS3.7/5.0/6.0 HV", "SMA LV", "Victron LV", "SUNTECH LV", "Sungrow HV", "KACO_HV", "Studer LV", "SolarEdge LV", "Ingeteam HV", "Sungrow LV", "Schneider LV", "SMA SBS2.5 HV", "Solis LV", "Solis HV", "SMA STP 5.0-10.0 SE HV", "Deye LV", "Phocos LV", "GE HV", "Deye HV", "Raion LV", "KACO_NH", "Solplanet", "Western HV", "SOSEN", "Hoymiles LV", "Hoymiles HV", "SAJ HV" ]
APPLICATION_LIST = [ "Off Grid", "On Grid", "Backup" ]
PHASE_LIST = [ "Single", "Three" ]

MAX_MODULES = 8
BMU_INDEX = 0x0000
BMS1_INDEX = 0x0001
BMS2_INDEX = 0x0002

ERRORS = [ "Cells Voltage Sensor Failure","Temperature Sensor Failure","BIC Communication Failure","Pack Voltage Sensor Failure","Current Sensor Failure","Charging Mos Failure","DisCharging Mos Failure","PreCharging Mos Failure","Main Relay Failure","PreCharging Failed","Heating Device Failure","Radiator Failure","BIC Balance Failure","Cells Failure","PCB Temperature Sensor Failure","Functional Safety Failure" ]
WARNINGS = [ "Battery Over Voltage","Battery Under Voltage","Cells OverVoltage","Cells UnderVoltage","Cells Imbalance","Charging High Temperature(Cells)","Charging Low Temperature(Cells)","DisCharging High Temperature(Cells)","DisCharging Low Temperature(Cells)","Charging OverCurrent(Cells)","DisCharging OverCurrent(Cells)","Charging OverCurrent(Hardware)","Short Circuit","Inversly Connection","Interlock switch Abnormal","AirSwitch Abnormal" ]
WARNINGS3 = [ "Battery Over Voltage","Battery Under Voltage","Cell Over Voltage","Cell Under Voltage","Voltage Sensor Failure","Temperature Sensor Failure","High Temperature Discharging (Cells)","Low Temperature Discharging (Cells)","High Temperature Charging (Cells)","Low Temperature Charging (Cells)","Over Current Discharging","Over Current Charging","Main circuit Failure","Short Circuit Alarm","Cells ImBalance","Current Sensor Failure" ]

def WORKING_AREA(area):
	if area == 1:
		return 'A'
	return 'B'

def bitmask_str(bitm, bitmaskList):
	warn = []
	for bit in range(16):
		if bitm & (1<<bit):
			warn.append(bitmaskList[bit])
	if len(warn):
		return ';'.join(warn)
	return 'Normal'

def signed16bit(val):
	if val >= 0x8000:
		val -= 0x10000
	return val

while True:
	modbusRegs = loadRegs(0x0000, 0x66)
	modbusRegs.update(loadRegs(0x0500, 25))

	bmuSerial = readRegBytes(0,18).decode('ascii')
	if bmuSerial.startswith('P03') or bmuSerial.startswith('E0P3'):
		BAT_Type = 'P3' # Modules in Serial
		batteryType = ['HVL','HVM','HVS']
	if bmuSerial.startswith('P02') or bmuSerial.startswith('P011'):
		BAT_Type = 'P2' # Modules in Parallels
		batteryType = ['LVL','LVFlex(Lite)','LVS/LVS Lite']
	MODULE_Count = modbusRegs[0x0010] & 0x0F

	# Supported Inverter by Battery type:
	# Battery HVM/HVS: [ "Fronius HV", "Goodwe HV/Viessmann HV", "KOSTAL HV", "SMA SBS3.7/5.0/6.0 HV", "Sungrow HV", "KACO_HV", "Ingeteam HV", "SMA SBS2.5 HV", "Solis HV", "SMA STP 5.0-10.0 SE HV", "GE HV", "Deye HV", "KACO_NH", "Solplanet", "Western HV", "SOSEN", "Hoymiles HV" ]
	# Battery HVL: [ "Goodwe HV/Viessmann HV", "SMA SBS3.7/5.0/6.0 HV", "Solis HV", "GE HV", "SAJ HV" ]
	# Battery LVL: [ "Selectronic LV", "SMA LV", "Victron LV", "Studer LV", "Schneider LV", "Solis LV", "Deye LV", "Raion LV", "Hoymiles LV" ]
	# Battery LVS/LVS Lite: [ "Goodwe LV/Viessmann LV", "Selectronic LV", "SMA LV", "Victron LV", "Studer LV", "SolarEdge LV", "Sungrow LV", "Schneider LV", "Deye LV", "Raion LV", "Hoymiles LV" ]
	# Battery LVFlex(Lite): [ "Selectronic LV", "SMA LV", "Victron LV", "Studer LV", "Deye LV", "Phocos LV", "Raion LV", "Hoymiles LV" ]

	if False: # hardware info and configuration
		print('%20s : %s' % ('Serial',bmuSerial))
		print('%20s : %s' % ('BAT_Type',BAT_Type))
		print('%20s : V%d.%d' % ('BMU A version',modbusRegs[0x000C] >> 8,modbusRegs[0x000C] & 0xFF))
		print('%20s : V%d.%d' % ('BMU B version',modbusRegs[0x000D] >> 8,modbusRegs[0x000D] & 0xFF))
		print('%20s : V%d.%d' % ('BMS version',modbusRegs[0x000E] >> 8,modbusRegs[0x000E] & 0xFF))
		print('%20s : BMU %s/BMS %s' % ('Working Area', WORKING_AREA(modbusRegs[0x000f] >> 8), WORKING_AREA(modbusRegs[0x000f] & 0xFF)))
		print('%20s : %d' % ('Module Qty', MODULE_Count))
		print('%20s : %d' % ('BMS Qty', (modbusRegs[0x0010] >> 4) & 0x0F))
		print('%20s : %s' % ('Inverter', INVERTER_LIST[(modbusRegs[0x0010] >> 8) & 0x0F]))
		print('%20s : %s' % ('Application', APPLICATION_LIST[(modbusRegs[0x0011] >> 8) & 0xFF]))
		print('%20s : %s' % ('Battery', batteryType[modbusRegs[0x0011] & 0xFF]))
		print('%20s : %s' % ('Phase', PHASE_LIST[((modbusRegs[0x0012] >> 8) & 0xFF)]))
		print('%20s : $%04x' % ('Adr',modbusRegs[0x004B]))
		print('%20s : $%04x' % ('BMU MCU Type',modbusRegs[0x004C]))
		print('%20s : $%04x' % ('BMS MCU Type',modbusRegs[0x004D]))
	if False: # current time seems to be unused. The Be Connect Plus software just prints the current time of the computer…
		b = datetime.datetime((modbusRegs[0x63] >> 8)+2000, modbusRegs[0x63] & 0xff, modbusRegs[0x64] >> 8, modbusRegs[0x64] & 0xff,modbusRegs[0x65] >> 8,modbusRegs[0x65] & 0xff, 0)
		print('%20s : %s' % ('Date/Time',b))
	if True: # current status
		print('%20s : %d%%' % ('State of Charge',modbusRegs[0x0500]))
		print('%20s : %.2fV' % ('Max. cell voltage',modbusRegs[0x0501] * 0.01))
		print('%20s : %.2fV' % ('Min. cell voltage',modbusRegs[0x0502] * 0.01))
		print('%20s : %d%%' % ('State of Health',modbusRegs[0x0503]))
		print('%20s : %.1fA' % ('Current', signed16bit(modbusRegs[0x0504]) * 0.1))
		print('%20s : %.2fV' % ('BAT Voltage',modbusRegs[0x0505] * 0.01))
		print('%20s : %d℃' % ('Max. cell temp',modbusRegs[0x0506]))
		print('%20s : %d℃' % ('Min. cell temp',modbusRegs[0x0507]))
		print('%20s : %d℃' % ('BMU temp',modbusRegs[0x0508]))
		if False:
			print('%20s : V%d.%d' % ('BMU version',modbusRegs[0x050a] >> 8,modbusRegs[0x050a] & 0xFF))
		print('%20s : $%04x' % ('Error Bitmask',modbusRegs[0x050d]))
		if False:
			print('%20s : V%d.%d' % ('P/T version',modbusRegs[0x050e] >> 8,modbusRegs[0x050e] & 0xFF))
		print('%20s : %.2fV' % ('Output Voltage',modbusRegs[0x0510] * 0.01))
		print('%20s : %.2fW' % ('Power',signed16bit(modbusRegs[0x0504]) * 0.1 * modbusRegs[0x0510] * 0.01))
		print('%20s : %d' % ('Charge Cycles',modbusRegs[0x0511]))
		print('%20s : %d' % ('Discharge Cycles',modbusRegs[0x0513]))

	if False: # BMS Info
		client.write_registers(0x0550, [BMS1_INDEX,0x8100], slave=1)
		while readRegs(0x0551)[0] != 0x8801: # wait for the response
			time.sleep(.1)
		Data = []
		for _ in range(0,5):
			Data = Data + readRegs(0x0558,0x41)[1:] # ignore length at the beginning (always 128)
		#print(Data)
		print('%20s : %.3fV (Cell #%d)' % ('Cell V-Max', Data[0] * 0.001,Data[2] >> 8))
		print('%20s : %.3fV (Cell #%d)' % ('Cell V-Min', Data[1] * 0.001,Data[2] & 0xFF))
		print('%20s : %d℃ (Cell #%d)' % ('Cell T-Max', Data[3],Data[5] >> 8))
		print('%20s : %d℃ (Cell #%d)' % ('Cell T-Min', Data[4],Data[5] & 0xFF))
		if False:
			print('%20s : $%02x' % ('SOC Calibration', Data[18] >> 8))
		#duplicate print('%20s : %.1fV' % ('BAT Voltage', Data[20] * 0.1))
		if False:
			print('%20s : $%02x' % ('Switch State', Data[22] & 0xFF))
		#duplicate print('%20s : %.1fV' % ('V-Out', Data[23] * 0.1))
		print('%20s : %.1f%%' % ('SOC', Data[24] * 0.1))
		#duplicate print('%20s : %.1fA' % ('Current', signed16bit(Data[26]) * 0.1))
		print('%20s : %s' % ('Warning 1', bitmask_str(Data[27], WARNINGS)))
		print('%20s : %s' % ('Warning 2', bitmask_str(Data[28], WARNINGS)))
		print('%20s : %s' % ('Warning 3', bitmask_str(Data[29], WARNINGS3)))
		if False:
			print('%20s : V%d.%dA' % ('BMS A', Data[30] >> 8, Data[30] & 0xFF))
			print('%20s : V%d.%dB' % ('BMS B', Data[31] >> 8, Data[31] & 0xFF))
			print('%20s : %s' % ('Working Area', WORKING_AREA(Data[32])))
			print('%20s : V%d.%d' % ('Threshold Table A', Data[45] >> 8, Data[45] & 0xFF))
			print('%20s : V%d.%d' % ('Threshold Table B', Data[46] >> 8, Data[46] & 0xFF))
		print('%20s : %s' % ('Fault', bitmask_str(Data[47], ERRORS)))
		if False:
			for m in range(0,MODULE_Count):
				print('%20s : ' % ('Module %d Voltage' % (m+1)), end='')
				cellVstr = []
				for i in range(0,16):
					cellVstr.append('%dmV' % (Data[48+m*16+i]))
				print(', '.join(cellVstr))
				print('%20s : ' % ('Module %d Temps' % (m+1)), end='')
				cellTstr = []
				for i in range(0,4):
					cellTstr.append('%d℃' % (Data[177+m*4+i] >> 8))
					cellTstr.append('%d℃' % (Data[177+m*4+i] & 0xff))
				print(', '.join(cellTstr))
	
	if False: # read history
		mode = BMU_INDEX

		# Read BMS History for BMS#$XXYY with XXYY = 1…x, BMU = 0x0000
		# 01 10 05A0 0002 04 XXYY 8100 CRC
		# Read 0x05A1 (Error Status?). It has to contain 0x8801 as OK
		# The read 5 times 0x05A8/0x0041 (read 65 words). Word 0 is 128 = package size in bytes

		if mode == BMU_INDEX:
			CODES = { 0:"Power ON", 1:"Power OFF", 2:"Events record", 4:"Start Charging", 5:"Stop Charging", 6:"Start DisCharging", 7:"Stop DisCharging", 0x20:"System status changed", 0x21:"Erase BMS Firmware", 0x24:"Functional Safety Info", 0x26:"SOP Info", 0x27:"BCU Hardware failt", 0x65:"Firmware Start to Update", 0x66:"Firmware Update Successful", 0x67:"Firmware Update failure", 0x68:"Firmware Jumpinto other section", 0x69:"Parameters table Update", 0x6a:"SN Code Changed", 0x6f:"DateTime Calibration", 0x70:"BMS disconnected with BMU", 0x71:"BMU F/W Reset", 0x72:"BMU Watchdog Reset", 0x73:"PreCharge Failed", 0x74:"Address registration failed", 0x75:"Parameters table Load Failed", 0x76:"System timing log", 0x78:"Parameters table updating done" }
		else:
			CODES = { 0:"Power ON", 1:"Power OFF", 2:"Events record", 3:"Timing Record", 4:"Start Charging", 5:"Stop Charging", 6:"Start DisCharging", 7:"Stop DisCharging", 8:"SOC calibration rough", 9:"SOC calibration fine", 10:"SOC calibration Stop", 0xb:"CAN Communication failed", 0xc:"Serial Communication failed", 0xd:"Receive PreCharge Command", 0xe:"PreCharge Successful", 0xf:"PreCharge Failure", 0x10:"Start end SOC calibration", 0x11:"Start Balancing", 0x12:"Stop Balancing", 0x13:"Address Registered", 0x14:"System Functional Safety Fault", 0x15:"Events additional info", 0x65:"Start Firmware Update", 0x66:"Firmware Update finish", 0x67:"Firmware Update fails", 0x68:"Firmware Jumpinto other section", 0x69:"Parameters table Update", 0x6a:"SN Code was Changed", 0x6b:"Current Calibration", 0x6c:"Battery Voltage Calibration", 0x6d:"PackVoltage Calibration", 0x6e:"SOC/SOH Calibration", 0x6f:"DateTime Calibration" }
		maxLen = len(max(CODES.values(), key=len))

		client.write_registers(0x05A0, [mode,0x8100], slave=1)
		while readRegs(0x05A1)[0] != 0x8801: # wait for the response
			time.sleep(.1)
		Data = bytearray()
		for _ in range(0,5):
			Data = Data + readRegBytes(0x05A8,0x41*2)[2:] # ignore length at the beginning (always 128)
		for i in range(0,22):
			s = Data[i*30:(i+1)*30]
			if len(s) == 30:
				print('%02d:%02d:%02d %2d.%02d.%4d : %02x %-*s : %s' % (s[4], s[5], s[6], s[3], s[2], s[1]+2000, s[0], maxLen, CODES[s[0]], binascii.hexlify(s[7:]).decode('ascii')))

	print('-' * 40)
	time.sleep(10)

client.close()
