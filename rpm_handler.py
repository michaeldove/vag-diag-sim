block_scaler = {0x01 : lambda a, b: a * b / 5.0}
block_id_name = {0x01: 'RPM'}




def handle_block(block):
    value_id = block[0]
    value_a, value_ block[1:2]
	value = block_scaler[value_id]
    name = block_id_name[value_id]
    return (name, value)
