from __future__ import print_function
import struct
import time
import can

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

KWP_READ_ECU_ID = 0x1a
KWP_ECU_ID_VAG_NUMBER_3 = 0x9a
KWP_ECU_ID_VAG_NUMBER_1 = 0x9b
KWP_ECU_ID_VAG_NUMBER_2 = 0x91

remote_arbitration_id = None
controller = None
kwp_resp_seq = 0

bus = can.interface.Bus(channel='slcan0', bustype='socketcan')

def send(message):
	time.sleep(0.0005)
	try:
		bus.send(message)
		print("Message sent {}".format(message))
	except can.CanError:
		print("Message NOT send")

def str_to_bytes(text):
    import array
    return array.array('B', text)

def chunk(arr, n):
    for i in xrange(0, len(arr), n):
        yield arr[i:i + n]
    

def channel_handler(message):
    global kwp_resp_seq, remote_arbitration_id
    opcode = message.data[0]
    if opcode == CHANNEL_PARAMS_REQ:
        msg = can.Message(arbitration_id=remote_arbitration_id,
						  data=[CHANNEL_PARAMS_RESP, 0x0f, 0x8a, 0xff, 0x4a, 0xff],
						  extended_id=False)
        send(msg)
        print("Send channel params response")
    elif opcode == CHANNEL_CLOSE_REQ:
        print("Close channel")
        kwp_resp_seq = 0
        remote_arbitration_id = None
    elif opcode & 0xf0 == 0x10: # Data packet
        kwp_opcode = message.data[3]
        ecu_id_type = message.data[4] 
        req_seq = opcode & 0x0f
        if kwp_opcode == KWP_READ_ECU_ID:
            data = None
            if ecu_id_type == KWP_ECU_ID_VAG_NUMBER_1:
                data = [[0x00, 0x30, 0x5a, 0x9b, 0x38, 0x50, 0x30],
                        [0x39, 0x30, 0x37, 0x31, 0x31, 0x35, 0x41],
                        [0x51, 0x20, 0x30, 0x30, 0x31, 0x30, 0x10],
                        [0x00, 0x00, 0x00, 0x01, 0xdc, 0x5a, 0x10],
                        [0x00, 0xbf, 0x32, 0x2e, 0x30, 0x6c, 0x20],
                        [0x52, 0x34, 0x2f, 0x34, 0x56, 0x20, 0x54],
                        [0x46, 0x53, 0x49, 0x20, 0x20, 0x20, 0x20],
                        [0x20]]
            elif ecu_id_type == KWP_ECU_ID_VAG_NUMBER_2:
                #data = str_to_bytes("Underground")
                data = [[0x00, 0x11, 0x5a, 0x91, 0x0e, 0x38, 0x50],
                        [0x30, 0x39, 0x30, 0x37, 0x31, 0x31, 0x35],
                        [0x42, 0x20, 0x20, 0x20, 0xff]]
            elif ecu_id_type == KWP_ECU_ID_VAG_NUMBER_3:
                data = [[0x00, 0x17, 0x5a, 0x9a, 0x01, 0xdc, 0x5a],
                        [0x10, 0x00, 0xbf, 0x30, 0x30, 0x31, 0x30],
                        [0x10, 0x09, 0x01, 0x03, 0x00, 0x0c, 0x18],
                        [0x0f, 0x01, 0x60, 0xff]]
            else:
                import pdb;pdb.set_trace()

            if req_seq > 0:
                seq = (req_seq + 1) & 0x0f
                resp_opcode = 0xb0 | seq
                msg = can.Message(arbitration_id=remote_arbitration_id,
                                  data=[resp_opcode],
                                  extended_id=False)
                send(msg)


            for i in range(len(data)):
                sequence_code = 0x20
                if i == len(data) -1:
                    sequence_code = 0x10
                data_row = data[i]
                if i == 0:
                    data_row = [0x00, len(data)] + data_row
                resp_opcode = sequence_code | kwp_resp_seq
                msg = can.Message(arbitration_id=remote_arbitration_id,
                                  data=[resp_opcode] + data[i],
                                  extended_id=False)
                kwp_resp_seq = (kwp_resp_seq + 1) & 0xf
                send(msg)
            ack = bus.recv()
            if ack.data[0] == (0xb0 & kwp_resp_seq):
                print("Message acknowledged by tester.")
            else:
                print("Expecting ack but got {}".format(message))
        elif kwp_opcode == 0x10 and ecu_id_type == 0x89:
            seq = (req_seq + 1) & 0x0f
            resp_opcode = 0xb0 | seq
            msg = can.Message(arbitration_id=remote_arbitration_id,
                              data=[resp_opcode],
                              extended_id=False)
            send(msg)

            data = [[0x00, 0x02, 0x50, 0x89]]

            for i in range(len(data)):
                sequence_code = 0x20
                if i == len(data) -1:
                    sequence_code = 0x10
                resp_opcode = sequence_code | kwp_resp_seq
                msg = can.Message(arbitration_id=remote_arbitration_id,
                                  data=[resp_opcode] + data[i],
                                  extended_id=False)
                kwp_resp_seq = (kwp_resp_seq + 1) & 0xf
                send(msg)
            ack = bus.recv()
            if ack.data[0] == (0xb0 & kwp_resp_seq):
                print("Message acknowledged by tester.")
            else:
                print("Expecting ack but got {}".format(message))

        elif kwp_opcode == 0x31 and ecu_id_type == 0xb8: # basic measuring blocks + more
            seq = (req_seq + 1) & 0x0f
            resp_opcode = 0xb0 | seq
            msg = can.Message(arbitration_id=remote_arbitration_id,
                              data=[resp_opcode],
                              extended_id=False)
            send(msg)

            data = [[0x00, 0x12, 0x71, 0xb8, 0x01, 0x01, 0x01],
                    [0x03, 0x01, 0x02, 0x01, 0x06, 0x01, 0x07],
                    [0x01, 0x08, 0x01, 0x0d, 0x01, 0x18]]

            for i in range(len(data)):
                sequence_code = 0x20
                if i == len(data) -1:
                    sequence_code = 0x10
                resp_opcode = sequence_code | kwp_resp_seq
                msg = can.Message(arbitration_id=remote_arbitration_id,
                                  data=[resp_opcode] + data[i],
                                  extended_id=False)
                kwp_resp_seq = (kwp_resp_seq + 1) & 0xf
                send(msg)
            ack = bus.recv()
            if ack.data[0] == (0xb0 & kwp_resp_seq):
                print("Message acknowledged by tester.")
            else:
                print("Expecting ack but got {}".format(message))



    elif opcode == 0xa3: #keep alive packet
        msg = can.Message(arbitration_id=remote_arbitration_id,
                          data=[0xa1, 0x0f, 0x8a, 0xff, 0x4a, 0xff],
                          extended_id=False)
        send(msg)
    else:
        print("Unknown opcode {}".format(hex(opcode)))

def set_remote_arbitration_id(message):
	global remote_arbitration_id
	remote_logical_id = message.data[5]
	remote_arbitration_id = remote_logical_id << 8

def setup_channel(message):
    print("Setting up channel")
    if remote_arbitration_id is None:
        set_remote_arbitration_id(message)
        remote_logical_id = message.data[5]
        msg = can.Message(arbitration_id=OPEN_CONTROLLER_ADDRESS_RESP,
						  data=[0, 0xd0,
								0x00, remote_logical_id,
								0x40, MY_CHANNEL_ADDRESS, 0x01],
						  extended_id=False)
        print(msg)
        send(msg)
    else:
        print("I already have an arbitration ID, maybe channel is already setup.")

def controller_ident_handler(message):
    set_remote_arbitration_id(message)
    msg = can.Message(arbitration_id=0x021f,
						  data=[0x00, 0xd0, 0x00, 0x03, 0x2e, 0x03, 0x01],
						  #data=[0xa1, 0x0f, 0x8a, 0xff, 0x4a, 0xff],
						  extended_id=False)
    send(msg)

def engine_controller_handler(message):
	opcode = message.data[1]
	if opcode == CHANNEL_SETUP_OPCODE:
		setup_channel(message)
		controller = ENGINE_CONTROLLER

def open_controller_handler(message):
	controller_id = message.data[0]
	controller_handlers[controller_id](message)

	

def handle_message(message):
	print("Received message {}".format(message))
	print ("Arbitration ID: {}".format(hex(message.arbitration_id)))
	arbitration_handlers[message.arbitration_id](message)

def receive_message():
	message = bus.recv()
	handle_message(message)
	
def send_one():
	msg = can.Message(arbitration_id=0xc0ffee,
					  data=[0, 25, 0, 1, 3, 1, 4, 1],
					  extended_id=True)
	send(msg)

arbitration_handlers = {OPEN_CONTROLLER_ADDRESS : open_controller_handler,
						MY_ADDRESS : channel_handler,
                        MY_CHANNEL_ADDRESS_DOUBLE: channel_handler }
controller_handlers = {ENGINE_CONTROLLER : engine_controller_handler,
					   CONTROLLER_IDENT_REQ: controller_ident_handler}

if __name__ == "__main__":
	while 1:
		receive_message()
