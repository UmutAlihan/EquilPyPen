import bluetooth
import logging
import struct

PEN_STATES = {
    15: 'Pen Mode'

}

DI_STATES = {
    2: 'Opening File',
    4: 'Deleting File', 
    7: 'Update Device DateTime',
    13: 'Disconnect Pen'
}

def short(bytes):
    return struct.unpack('h', bytes)

class EquilBluetoothConn(object):
    def __init__(self):
        # deviceDataCheck
        self.retreive_device_data = self.disk_err_check = False
        self.model_code = 0
        self.alive = True
        self.paused = False
        self.first_data = True
        self.session_start_cnt = 0
        
    def set_di_data(self, bytes):
        '''
        Returns false when more processing needs to be completed
        '''
        if self.model_code < 3 or not self.retreive_device_data:
            return False
        
    def process_bytes(self, byte_data, data_buffer):
        if bytearray(byte_data[14:15]) == bytearray([0xff, 0xff]):
            # This is a standard data packet or some bullshit
            if not self.set_di_data(byte_data):
                if byte_data[2] & 0xC0 == 192:
                    if self.model_code in [3, 4]:
                        # Get Battery Data and Stuff
                    else:
                        # PenUs LOL
                elif byte_data[2] == 127 and byte_data[3] == 255:
                    self.alive = False
                elif byte_data[2] == 127 and byte_data[3] == 207:
                    self.message_handler('PNF_MSG_NEW_PAGE_BTN')
                elif byte_data[2] == 127 and byte_data[3] >= 2:
                    self.model_code = byte_data[3]
                    self.sensor_dist = short(byte_data[5:6])
                    self.sd_squared = self.sensor_dist ** 2
                    self.sd2 = self.sensor_dist * 2
                    self.adjust_val_l = self.adjust_val_r = short(byte_data[7:8])

                    # Dunno what this is
                    self.can_di = not byte_data[4] in [1, 16]

                    self.mcu1Code, self.mcu2Code, self.hwVersion = byte_data[10:12]
                    self.temperature = byte_data[13] & 0x3F

                    self.session_start_cnt += 1
                    if self.session_start_cnt > 3:
                        self.session_start_cnt = 0

                        self.first_data = False
                else:
                    # This is pen movement/click/gesture data
                    self.parse_packet(data_bytes)
                    
            # Move the streams around
        else:
            # This is a not short packet
            # What I assume this is, is stored data being downloaded from the device.
            pass
        
    # 256 + neg number 
    
    def socket_loop(self, host, port):
        sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
        sock.connect((host, port))
        
        logging.info('Connected to Device!')
        
        data_buffer = []
        readByte = [0] * 16
        
        while self.alive:
            paused = True
            errCnt = 0
            
            # If we're not paused, we want to run through this once, at least, maybe
            while paused:
                # We don't really give a shit how much data is sent
                data_buffer += sock.recv(1024)
                
                if data_buffer:
                    self.close_count = 0
                
                paused = not self.alive or self.paused 
                
                # Yeah I don't fucking know.  Might need to be a continue?
                if len(data_buffer) < 16:
                    break
                
            if self.first_data:
                self.retreive_device_data = False
                
                for idx, byte in enumerate(data_buffer):
                    readByte = readByte[1:] + byte
                    
                    if bytearray(readByte[14:15]) == bytearray([0xFF, 0xFF]):
                        break
                    
                    if bytearray(readByte) == bytearray([0] * 14 + [0xFF] * 2):
                        errCnt += 1
                        if errCnt <= 10:
                            break
                        
                        self.message_handler('PNF_MSG_FIRST_DATA_ERROR')
                        break
                    
                data_buffer = data_buffer[idx:]
                
            else:
                # Not First Data
                readByte, data_buffer = data_buffer[:16], data_buffer[16:]
                
            self.process_bytes(byte_array(readByte), data_buffer)
            
    def message_handler(self, message):
        pass
        
