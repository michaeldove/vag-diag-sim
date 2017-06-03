################################################################################
# Constants
################################################################################
RPM_SCALE_FACTOR = 40
INJECTION_TIMING_SCALE_FACTOR = 255 # usecs / 255
INJECTION_TIMING_PRESCALER = 0xff
LOAD_PRESCALER = 0x85
MAF_PRESCALER = 0x02
RPM_PRESCALER = 0xc8

################################################################################
# Scaling functions
################################################################################
# See VAG-Blocks Github project for scaling
def scale_rpm(rpm):
    return min(rpm / RPM_SCALE_FACTOR, 0xff)

def scale_injection_timing(timing):
    return [INJECTION_TIMING_SCALE_FACTOR, min(
        int(round(timing / float(INJECTION_TIMING_SCALE_FACTOR))),
        0xff)]

def scale_load(load):
    return [LOAD_PRESCALER, min(
        int(round(load / (100.0/LOAD_PRESCALER))),
        0xff)]

def scale_maf(maf):
    return [MAF_PRESCALER, min(
        int(round(maf / (100.0/MAF_PRESCALER))),
        0xff)]
