# Minimal boot.py for the device (replaces UIFlow2's stock boot.py).
#
# The stock file watches for a held button at startup and permanently
# switches the device to the UIFlow setup menu — which is exactly what
# the side power button does, so pressing it "bricked" the app. The
# stock file's own comments bless deleting it. With this in place,
# every boot goes straight to main.py, and the side button becomes
# the flashcard gesture (see scheduler.woke_by_timer).
#
# Deployed to the device as /flash/boot.py.
