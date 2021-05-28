from imutils.video import VideoStream
from pyzbar import pyzbar
import imutils
import cv2
import serial
import sqlite3

canteenDB = 'databases/Canteen.db'
emDB = 'databases/wearoDB.db'
#Initialize Cart Variable
cart = []

#Initialize GPIO Serial of Pi and flush any previous data in the bus
ser = serial.Serial('/dev/ttyS0', 9600, timeout=1)
ser.flush()
    
while True:
    #Wait for data from RFID Module
    if ser.in_waiting > 0:
        #Read the RFID Tag
        RFIDTAG = ser.readline().decode('utf-8').rstrip()
        print(RFIDTAG)

        #Connect to the Sqlite3 Database
        conn = sqlite3.connect(emDB)
        cur = conn.cursor()
        
        #Employe ID and Name
        EID = 0
        name = ""
        
        #try to fetch the employee details with the RFID Tag
        try:
            cur.execute("SELECT ID, NAME FROM EmployeList WHERE RFID='%s'" % (RFIDTAG))
            EID, name = cur.fetchone()
            print("EID: ", EID, "Name: ", name)
        except:
            print("INVALID RFID DETECTED")
            break
        
        #if Employe exists then continue
        if name != "":
            # initialize the video stream and allow the camera sensor to warm up
            print("Starting video stream...")
            vs = VideoStream(usePiCamera=True).start()
            time.sleep(2.0)
            
            #loop until the RFID tag is scanned again
            while ser.in_waiting == 0:
                # grab the frame from the threaded video stream and resize it to
                # have a maximum width of 400 pixels
                frame = vs.read()
                frame = imutils.resize(frame, width=400)
                ret, bw_im = cv2.threshold(frame, 127, 255, cv2.THRESH_BINARY)
                
                # find the qrcodes/barcodes in the frame and decode each of the barcodes
                qrcodes = pyzbar.decode(bw_im)

                # decode the detected qrcodes/barcodes
                for qrcode in qrcodes:
                    qrData = qrcode.data.decode("utf-8")
                    qrType = qrcode.type
                    
                    print("QRCode Data: ", qrData, " QRCode Type: ", qrType)

                    flag = 1
                    for i in range(len(cart)):
                        #Check if the item is already in cart
                        if cart[i]['Product'] == qrData:
                            #Then increment quantity by one and find total
                            cart[i]['Quantity'] += 1
                            cart[i]['Total'] = cart[i]['Price']*cart[i]['Quantity']
                            flag = 0
                            break;
                    #if new product, then add the product to cart
                    if flag == 1:
                        try:
                            cur.execute("SELECT Price from ProductList WHERE Product= '"+qrData+"'")
                            price = cur.fetchone()[0]
                            cart.append({'Product':qrData, 'Price': price, 'Quantity': 1, 'Total': price})
                        except:
                            print("INVALID QR CODE RECEIVED")
                        
                    time.sleep(1)
            
            print("Cart Confirmed")
            
            RFIDTAG_cl = ser.readline().decode('utf-8').rstrip()
            print(RFIDTAG_cl)
            #Check whether the card is same as the first scanned card
            while RFIDTAG_cl != RFIDTAG:
                print("Use the same card you initiated the shopping")
                while ser.in_waiting == 0:
                    pass
                RFIDTAG_cl = ser.readline().decode('utf-8').rstrip()

            #Print all the data
            print("Employe ID: ", EID, " NAME : ", name, " RFID: ", RFIDTAG)
            print("Your Purchase: ")
            GrandTotal = 0
            for i in range(len(cart)):
                print(i+1, " ", cart[i]['Product'], " ",cart[i]['Price'], cart[i]['Quantity'], cart[i]['Total'])
                GrandTotal += cart[i]['Total']
            print("Grant Total: ", GrandTotal)
                
            #Insert data to the Transaction Table            
            cur.execute("INSERT INTO TransactionList VALUES (julianday('now'), %s, %f)" % (RFIDTAG, GrandTotal))
            #Intiate exit procedures
            conn.commit()
            conn.close()
            cart = []
            vs.stop()
        else:
            pass
    else:
        pass