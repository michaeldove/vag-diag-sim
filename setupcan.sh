sudo slcan_attach -f -s6 -o /dev/ttyACM0
sudo slcand -s6 -S 1000000 ttyACM0 slcan0
sudo ifconfig slcan0 up
