from __future__ import print_function
import struct
import time
import can
from scale import *

ENGINE_CONTROLLER = 0x01 # more likely open controller
CONTROLLER_IDENT_REQ = 0x1f

CHANNEL_PARAMS_REQ = 0xa0
CHANNEL_PARAMS_RESP = 0xa1
CHANNEL_CLOSE_REQ = 0xa8
CHANNEL_SETUP_OPCODE = 0xc0

OPEN_CONTROLLER_ADDRESS = 0x200L
OPEN_CONTROLLER_ADDRESS_RESP = 0x0201
MY_ADDRESS = 0x32eL
MY_CHANNEL_ADDRESS = 0x07
MY_CHANNEL_ADDRESS_DOUBLE = 0x740L

UNKNOWN_ADDRESS_DOUBLE = 0x710L # Broadcast?

KWP_READ_ECU_ID = 0x1a
KWP_ECU_ID_VAG_NUMBER_3 = 0x9a
COMPONENT_ID= 0x9b
ECU_ID = 0x91

KWP_READ_MEASURING_BLOCK = 0x21
KWP_MEASURING_BLOCK_1 = 0x02
KWP_MEASURING_BLOCK_20 = 0x14
KWP_MEASURING_BLOCK_115 = 0x73

UNIT_PERCENT = 0x21
UNIT_PERCENT_2 = 0x17
UNIT_DEGREES = 0x22
UNIT_MS = 0x16
UNIT_GS = 0x19

remote_arbitration_id = None
controller = None
kwp_resp_seq = 0

bus = can.interface.Bus(channel='slcan0', bustype='socketcan')


def send(message):
	time.sleep(0.0055)
	try:
		bus.send(message)
		print("Message sent {}".format(message))
	except can.CanError:
		print("Message NOT send")

def str_to_bytes(text):
    import array
    return array.array('B', text)

def chunk(arr, n=7):
    for i in xrange(0, len(arr), n):
        yield arr[i:i + n]

def message(arbitration_id, data):
    return can.Message(arbitration_id=arbitration_id,
                      data=data,
                      extended_id=False)
    
def data_send(payload):
    """Send payload within a VWT Data Message."""
    global kwp_resp_seq
    data = [0x00, len(payload)] + payload
    segmented_data = list(chunk(data))
    for seq, msg_data in enumerate(segmented_data):
        sequence_code = 0x20
        is_last_seq = seq == len(segmented_data) - 1
        if is_last_seq:
            sequence_code = 0x10
        resp_opcode = sequence_code | kwp_resp_seq
        msg = message(remote_arbitration_id, [resp_opcode] + msg_data)
        kwp_resp_seq = (kwp_resp_seq + 1) & 0xf
        send(msg)
    ack = bus.recv()
    expected_ack = 0xb0 | kwp_resp_seq
    if ack.data[0] == expected_ack:
        print("Message acknowledged by tester.")
    else:
        print("Expecting ack {} but got {}".format(hex(expected_ack), ack))

def send_ack(last_seq):
    """Send VWTP acknowledgement packet."""
    seq = (last_seq + 1) & 0x0f
    resp_opcode = 0xb0 | seq
    msg = message(remote_arbitration_id, [resp_opcode])
    send(msg)

def null_handler(in_message):
    global remote_arbitration_id
    remote_arbitration_id = None

def channel_handler(in_message):
    global kwp_resp_seq, remote_arbitration_id
    opcode = in_message.data[0]
    if opcode == CHANNEL_PARAMS_REQ:
        msg = message(
            remote_arbitration_id,
            [CHANNEL_PARAMS_RESP, 0x0f, 0x8a, 0xff, 0x4a, 0xff])
        send(msg)
        print("Send channel params response")
    elif opcode == CHANNEL_CLOSE_REQ:
        print("Close channel")
        kwp_resp_seq = 0
        remote_arbitration_id = None
    elif opcode & 0xf0 == 0x10: # Data packet
        kwp_opcode = in_message.data[3]
        ecu_id_type = in_message.data[4] 
        req_seq = opcode & 0x0f
        if kwp_opcode == KWP_READ_ECU_ID:
            data = None
            if ecu_id_type == COMPONENT_ID:
                payload = [0x5a, COMPONENT_ID, 0x38, 0x50, 0x30,
                        0x39, 0x30, 0x37, 0x31, 0x31, 0x35, 0x41,
                        0x51, 0x20, 0x30, 0x30, 0x31, 0x30, 0x10,
                        0x00, 0x00, 0x00, 0x01, 0xdc, 0x5a, 0x10,
                        0x00, 0xbf, 0x32, 0x2e, 0x30, 0x6c, 0x20,
                        0x52, 0x34, 0x2f, 0x34, 0x56, 0x20, 0x54,
                        0x46, 0x53, 0x49, 0x20, 0x20, 0x20, 0x20,
                        0x20]
            elif ecu_id_type == ECU_ID:
                #data = str_to_bytes("Underground")
                payload = [0x5a, ECU_ID, 0x0e, 0x38, 0x50,
                        0x30, 0x39, 0x30, 0x37, 0x31, 0x31, 0x35,
                        0x42, 0x20, 0x20, 0x20, 0xff]
            elif ecu_id_type == KWP_ECU_ID_VAG_NUMBER_3:
                payload = [0x5a, 0x9a, 0x01, 0xdc, 0x5a,
                        0x10, 0x00, 0xbf, 0x30, 0x30, 0x31, 0x30,
                        0x10, 0x09, 0x01, 0x03, 0x00, 0x0c, 0x18,
                        0x0f, 0x01, 0x60, 0xff]
            else:
                import pdb;pdb.set_trace()

            if req_seq > 0:
                send_ack(req_seq)
            data_send(payload)

        elif kwp_opcode == 0x10 and ecu_id_type == 0x89:
            send_ack(req_seq)
            payload = [0x50, 0x89]
            data_send(payload)
            
        elif kwp_opcode == 0x31 and ecu_id_type == 0xb8: # basic measuring blocks + more
            send_ack(req_seq)
            payload = [0x71, 0xb8, 0x01, 0x01, 0x01,
                       0x03, 0x01, 0x02, 0x01, 0x06, 0x01, 0x07,
                       0x01, 0x08, 0x01, 0x0d, 0x01, 0x18]
            data_send(payload)
        elif kwp_opcode == KWP_READ_MEASURING_BLOCK: # advanced measuring block
            send_ack(req_seq)
            if ecu_id_type == KWP_MEASURING_BLOCK_1: # RPM, load, injection timing, MAF
                rpm = 3000
                injection_timing = 2000 #usecs
                load = 180
                maf = 2

                scaled_rpm = scale_rpm(rpm)
                scaled_injection_timing = scale_injection_timing(injection_timing)
                scaled_load = scale_load(load)
                scaled_maf = scale_maf(maf)
                payload = [0x61, 0x02, 0x01, RPM_PRESCALER, scaled_rpm,
                           UNIT_PERCENT, scaled_load[0], scaled_load[1],
                           UNIT_MS, scaled_injection_timing[0], scaled_injection_timing[1],
                           UNIT_GS, scaled_maf[0], scaled_maf[1],
                           0x25, 0x00, 0x00,
                           0x25, 0x04, 0x1d,
                           0x25, 0x02, 0x7a,
                           0x25, 0x00, 0x00]
                data_send(payload)
            elif ecu_id_type == KWP_MEASURING_BLOCK_20:
                payload = [0x61, KWP_MEASURING_BLOCK_20,
                           UNIT_DEGREES, 0x4b, 0xff,
                           UNIT_DEGREES, 0x4b, 0x80,
                           UNIT_DEGREES, 0x4b, 0x80,
                           UNIT_DEGREES, 0x4b, 0x80,
                           0x25, 0x00, 0x00,
                           0x25, 0x00, 0x00,
                           0x25, 0x00, 0x00,
                           0x25, 0x00, 0x00]
                data_send(payload)
            elif ecu_id_type == KWP_MEASURING_BLOCK_115:
                payload = [0x61, KWP_MEASURING_BLOCK_115,
                           0x01, 0xc8, 0x12,
                           0x21, 0x85, 0x19,
                           0x12, 0xfa, 0x22,
                           0x60, 0x64, 0xff, #65
                           0x36, 0x05, 0x02,
                           0x36, 0x03, 0x1e, 
                           0x36, 0x04, 0x22,
                           0x36, 0x04, 0xc7]
                data_send(payload)
                

    elif opcode == 0xa3: #keep alive packet
        msg = message(remote_arbitration_id, [0xa1, 0x0f, 0x8a, 0xff, 0x4a, 0xff])
        send(msg)
    else:
        print("Unknown opcode {}".format(hex(opcode)))

def set_remote_arbitration_id(in_message):
	global remote_arbitration_id
	remote_logical_id = in_message.data[5]
	remote_arbitration_id = remote_logical_id << 8

def setup_channel(in_message):
    print("Setting up channel")
    if remote_arbitration_id is None:
        set_remote_arbitration_id(in_message)
        remote_logical_id = in_message.data[5]
        data = [0x00, 0xd0, 0x00, remote_logical_id, 0x40, MY_CHANNEL_ADDRESS, 0x01]
        msg = message(OPEN_CONTROLLER_ADDRESS_RESP, data)
        send(msg)
    else:
        print("I already have an arbitration ID, maybe channel is already setup.")

def controller_ident_handler(in_message):
    set_remote_arbitration_id(in_message)
    msg = message(0x021f, [0x00, 0xd0, 0x00, 0x03, 0x2e, 0x03, 0x01])
    send(msg)

def engine_controller_handler(in_message):
	opcode = in_message.data[1]
	if opcode == CHANNEL_SETUP_OPCODE:
		setup_channel(in_message)
		controller = ENGINE_CONTROLLER

def open_controller_handler(in_message):
	controller_id = in_message.data[0]
	controller_handlers[controller_id](in_message)

	

def handle_message(in_message):
	#print("Received message {}".format(message))
	#print ("Arbitration ID: {}".format(hex(message.arbitration_id)))
	arbitration_handlers[in_message.arbitration_id](in_message)

def receive_message():
	in_message = bus.recv()
	handle_message(in_message)
	
arbitration_handlers = {OPEN_CONTROLLER_ADDRESS : open_controller_handler,
						MY_ADDRESS : channel_handler,
                        MY_CHANNEL_ADDRESS_DOUBLE: channel_handler,
                        UNKNOWN_ADDRESS_DOUBLE: null_handler }
controller_handlers = {ENGINE_CONTROLLER : engine_controller_handler,
					   CONTROLLER_IDENT_REQ: controller_ident_handler}

if __name__ == "__main__":
	while 1:
		receive_message()
