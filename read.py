import MFRC522
import signal

continue_reading = True

def uidToString(uid):
    mystring = ""
    for i in uid:
        mystring = format(i, '02X') + mystring
    return mystring


def end_read(signal, frame):
    global continue_reading
    print("Ctrl+C captured, ending read.")
    continue_reading = False

signal.signal(signal.SIGINT, end_read)

MIFAREReader = MFRC522.MFRC522()

print("Welcome to the MFRC522 data read example")
print("Press Ctrl-C to stop.")

while continue_reading:

    (status, TagType) = MIFAREReader.MFRC522_Request(MIFAREReader.PICC_REQIDL)

    if status == MIFAREReader.MI_OK:
        print ("Card detected")

        (status, uid) = MIFAREReader.MFRC522_SelectTagSN()
        if status == MIFAREReader.MI_OK:
            print("Card read UID: %s" % uidToString(uid))
        else:
            print("Authentication error")