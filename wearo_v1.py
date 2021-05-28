from flask import Flask, request, render_template, redirect, url_for
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import sqlite3
import datetime as dt
import os.path
import json

app = Flask(__name__)

mainDB = 'databases/wearoDB.db'
canteenDB = 'databases/Canteen.db'
admn_ID = '1';
admn_pass = '4321'
RSSIThreshold = -60;
app.secret_key = 'thisisaverysecretkey'
login_manager = LoginManager(app)
login_manager.init_app(app)
login_manager.login_view = 'index'

class User(UserMixin):
    def __init__(self, id, NAME, password):
         self.id = id
         self.NAME = NAME
         self.password = password
         self.authenticated = False
         def is_active(self):
             return self.is_active()
         def is_anonymous(self):
             return False
         def is_authenticated(self):
             return self.authenticated
         def is_active(self):
             return True
         def get_id(self):
             return self.id

@login_manager.user_loader
def load_user(user_id):
	conn = sqlite3.connect(mainDB)
	cur = conn.cursor()
	cur.execute("SELECT ID, NAME, PIN from EmList where ID = (?)",[user_id])
	lu = cur.fetchone()
	conn.close()
	if lu is None:
		return None
	else:
		return User(int(lu[0]), lu[1], lu[2])

@app.route('/spo2', methods = ['POST'])
def spo2():
	sensor = json.loads(request.data)
	print("ID : %d Spo2 : %d Temperature : %d " % (sensor['ID'], sensor['spo2'], sensor ['temp']))
	DB = 'databases/emdatabases/%d.db' % (sensor['ID'])
	# print(DB)
	try:
		conn = sqlite3.connect(DB)
	except:
		print('Database Busy!')
		return ''
	cur = conn.cursor()
	cur.execute("INSERT INTO SensorRead VALUES (datetime('now', 'localtime'), %d , %d)" %(sensor['spo2'], sensor ['temp']))
	conn.commit()
	return ''

@app.route('/prox', methods = ['POST'])
def prox():
 	proximity = json.loads(request.data)
 	print("ID : %d ProxID : %d RSSI : %d " % (proximity['ID'], proximity['proxID'], proximity['RSSI']))
 	DB = 'databases/emdatabases/%d.db' % (proximity['ID'])
 	conn = sqlite3.connect(DB)
 	cur = conn.cursor()
 	cur.execute("SELECT * FROM wearableList WHERE ID = '%d'" % (proximity['proxID']))
 	fetch = cur.fetchone()
 	print()
 	if fetch == None:
 		cur.execute("INSERT INTO wearableList VALUES (%d , %d)" % (proximity['proxID'], proximity['RSSI']))
 		conn.commit()
 		conn.close()
 	else:
 		cur.execute("UPDATE wearableList set RSSI = '%d' WHERE ID = '%d'" % (proximity['RSSI'], proximity['proxID']))
 		conn.commit()
 		conn.close()

 	conn = sqlite3.connect(mainDB)
 	cur = conn.cursor()
 	cur.execute("SELECT NAME FROM EmList WHERE ID = '%d'" % (proximity['proxID']))
 	NAME = cur.fetchone()[0]
 	conn.close()

 	if proximity['RSSI'] > RSSIThreshold and fetch[1] < RSSIThreshold:
 		try:
 			conn = sqlite3.connect(DB)
 		except:
 			print('Database Busy!')
 			return ''
 		cur = conn.cursor()
 		cur.execute("INSERT INTO Proximity VALUES (datetime('now', 'localtime'), %d , '%s')" %(proximity['proxID'], NAME))
 		conn.commit()
 		conn.close()
 	return ''

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/emlogin/<state>', methods = ['POST', 'GET'])
def emlogin(state):
	if current_user.is_authenticated:
		ID = current_user.get_id()
		return redirect(url_for('emdash',ID = ID))
	if state == 'null':
		return render_template('emlogin.html')

	elif state == 'check':
		try:
			ID = int(request.form['ID'])
			Pin = int(request.form['Pin'])
		except:
			templateData = {'LoginError': "Invalid ID/Pin"}
			return render_template('emlogin.html', **templateData)

		conn = sqlite3.connect(mainDB)
		cur = conn.cursor()

		try:
			cur.execute("SELECT PIN, NoofTry, DISABLED, BLOCKED FROM EmList WHERE ID= '%d'" % (ID))
			PIN_DB, NoofTry, Disabled, Blocked = cur.fetchone()
			conn.close()

			if int(Disabled) == 1:
				templateData = {'LoginError': "Account is Disabled!"}
				return render_template('emlogin.html', **templateData)

			elif int(Blocked) == 1:
				templateData = {'LoginError': "Account is Blocked!"}
				return render_template('emlogin.html', **templateData)

			elif Pin == int(PIN_DB):
				print("Succesful Login")
				Us = load_user(ID)
				# print(US)
				login_user(Us, remember=True)
				if int(NoofTry) == -1:
				   return redirect(url_for('changepin', state = 'null', ID = ID))
				else:
				   conn = sqlite3.connect(mainDB)
				   cur = conn.cursor()
				   cur.execute("UPDATE EmList set NoofTry = 0 WHERE ID= '%d'" % (ID))
				   conn.commit()
				   conn.close()
				   return redirect(url_for('emdash',ID = ID))

			elif Pin != int(PIN_DB):
				if int(NoofTry) != -1:
					print("Incorrect Pin")
					conn = sqlite3.connect(mainDB)
					cur = conn.cursor()
					Curr_NoofTry = int(NoofTry) + 1
					Blocked = 1 if Curr_NoofTry >= 3 else 0 
					try:
						cur.execute("UPDATE EmList set NoofTry = %d, BLOCKED = %d WHERE ID= '%d' " % (Curr_NoofTry, Blocked, ID))
						conn.commit()
						conn.close()
					except:
						conn.close()
						templateData = {'LoginError': 'Database Busy! Try in a few'}
						return render_template('emlogin.html', **templateData)
					templateData = {'LoginError': 'Incorrect Pin!'}
					return render_template('emlogin.html', **templateData)
				else:
					templateData = {'LoginError': 'Incorrect Pin!'}
					return render_template('emlogin.html', **templateData)
		except:
			print("Invalid Student ID")
			templateData = {'LoginError': 'Check Your Student ID!'}
			return render_template('emlogin.html', **templateData)

@app.route('/changepin/<state>/<int:ID>', methods = ['POST', 'GET'])
@login_required
def changepin(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))

	if state == 'null':
		templateData = {'ID':ID}
		return render_template('changepin.html', **templateData)
	elif state == 'check':
		try:
			NewPin = int(request.form['NewPin'])
			ConfirmPin = int(request.form['ConfirmPin'])
		except:
			templateData = {'Error': "Only numbers are allowed", 'ID':ID}
			return render_template('changepin.html', **templateData)
		if NewPin == ConfirmPin:
			conn = sqlite3.connect(mainDB)
			cur = conn.cursor()
			try:
				cur.execute("SELECT PIN FROM EmList WHERE ID='%d'" % (ID))
				PIN_DB = int(cur.fetchone()[0])
				if NewPin == PIN_DB:
					print("Same as previous password")
					templateData = {'Error':"Same as previous password", 'ID': ID }
					conn.close()
					return render_template('changepin.html', **templateData)
				else:
					cur.execute("UPDATE EmList set PIN = %d, NoofTry = 0 WHERE ID='%d'" % (NewPin, ID))
					conn.commit()
					conn.close()
					print("Pin Changed Succesfully")
					return redirect(url_for('emdash', ID = ID))
			except:
				print("Something went wrong")
				return redirect(url_for('emlogin', state = 'null'))
		else:
			print("Pins do not match")
			templateData = {'Error':"Pins do not match", 'ID': ID }
			return render_template('changepin.html', **templateData)

@app.route('/emdash/<int:ID>', methods = ['POST', 'GET'])
@login_required
def emdash(ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	conn = sqlite3.connect(mainDB)
	cur = conn.cursor()
	try:
		cur.execute("SELECT NAME, RFID FROM EmList WHERE ID= '%d'" % (ID))
		NAME, RFID = cur.fetchone()
		conn.close()
		templateData = {'ID' : ID, 'NAME' : NAME, 'RFID' : RFID}
		return render_template('emdash.html', **templateData)
	except:
		conn.close()
		return render_template('emdash.html')	

@app.route("/emdash/attendance/<state>/<int:ID>", methods=['POST'])
@login_required
def emattendance(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('emattendance.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(mainDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('emattendance.html', **templateData)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()
		SELECT = request.form['select']
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']
		# print("%s %s %s" %(SELECT,StartDate, EndDate))
		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass
		filters += " AND ID = '%d'" % (ID)
		if SELECT == 'PRESENT' or SELECT == 'ABSENT':
			filters += " AND STATUS = '%s'" % (SELECT)
		print(filters)
		try:
			cur.execute("SELECT * FROM AttendanceList %s" %(filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('emattendance.html', rows = rows, ID = ID)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('emattendance.html', ID = ID, **templateData)
			
@app.route("/emdash/sensor/<state>/<int:ID>", methods=['POST'])
@login_required
def sensor(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('sensor.html', ID = ID)
	elif state == 'check':
		DB = 'databases/emdatabases/%s.db' % (ID)
		# print(DB)
		try:
			conn = sqlite3.connect(DB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('sensor.html', **templateData, ID = ID)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']
		# print("%s %s %s" %(SELECT,StartDate, EndDate))
		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass
		print(filters)
		try:
			cur.execute("SELECT * FROM SensorRead %s" % (filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('sensor.html', ID = ID, rows = rows)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('sensor.html', ID = ID, **templateData)

@app.route("/emdash/proximity/<state>/<int:ID>", methods=['POST'])
@login_required
def proximity(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('proximity.html', ID = ID)
	elif state == 'check':
		DB = 'databases/emdatabases/%s.db' % (ID)
		# print(DB)
		try:
			conn = sqlite3.connect(DB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('proximity.html', **templateData, ID = ID)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()
		proxID = request.form['ID']
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']
		# print("%s %s %s" %(SELECT,StartDate, EndDate))
		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass
		if proxID != '':
			filters += " AND ID = '%s'" % (proxID)
		
		print(filters)
		try:
			cur.execute("SELECT * FROM Proximity %s" % (filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('proximity.html', ID = ID, rows = rows)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('proximity.html', ID = ID, **templateData)

@app.route("/emdash/canteen/<state>/<int:ID>", methods=['POST'])
@login_required
def canteen(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('canteen.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(canteenDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('canteen.html', **templateData, ID = ID)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']
		# print("%s %s %s" %(SELECT,StartDate, EndDate))
		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass

		filters += " AND ID = '%s'" % (ID)
		
		print(filters)
		try:
			cur.execute("SELECT * FROM Transactions %s" % (filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('canteen.html', ID = ID, rows = rows)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('canteen.html', ID = ID, **templateData)

@app.route("/emdash/logout", methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/adminlogin/<state>', methods = ['POST', 'GET'])
def adminlogin(state = 'null'):
	if current_user.is_authenticated:
		ID = current_user.get_id()
		return redirect(url_for('admdash',ID = ID))
	if state == 'null':
		return render_template('adminlogin.html')
	elif state == 'check':
		Pin = request.form['Pin']
		if Pin == admn_pass:
			Us = load_user(int(admn_ID))
			login_user(Us, remember=True)
			return redirect(url_for('admdash', ID = int(admn_ID)))
		else:
			templateData = {'LoginError':'Wrong Pin'}
			return render_template('adminlogin.html', **templateData)

@app.route('/admdash/<int:ID>', methods = ['POST', 'GET'])
@login_required
def admdash(ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	return render_template('admdash.html', ID = ID)	

@app.route("/admdash/attendance/<state>/<int:ID>", methods=['POST'])
@login_required
def admttendance(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('admattendance.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(mainDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('admattendance.html', **templateData)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()
		emID = request.form['emID']
		SELECT = request.form['select']
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']
		# print("%s %s %s" %(SELECT,StartDate, EndDate))
		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass
		if emID != '':
			filters += " AND ID = '%s'" % (emID)
		if SELECT == 'PRESENT' or SELECT == 'ABSENT':
			filters += " AND STATUS = '%s'" % (SELECT)
		print(filters)
		try:
			cur.execute("SELECT * FROM AttendanceList %s" %(filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('admattendance.html', rows = rows, ID = ID)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('admattendance.html', ID = ID, **templateData)
			
@app.route("/admdash/sensor/<state>/<int:ID>", methods=['POST'])
@login_required
def admsensor(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('admsensor.html', ID = ID)
	elif state == 'check':
		emID = request.form['emID']
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']

		DB = 'databases/emdatabases/%s.db' % (emID)
		if os.path.exists(DB) == False:
			templateData = {'Error': "ID Doesn't exists"}
			return render_template('admsensor.html', **templateData, ID = ID) 
		# print(DB)
		try:
			conn = sqlite3.connect(DB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('admsensor.html', **templateData, ID = ID)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()

		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass
		print(filters)
		try:
			cur.execute("SELECT * FROM SensorRead %s" % (filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('admsensor.html', ID = ID, rows = rows)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('admsensor.html', ID = ID, **templateData)

@app.route("/admdash/proximity/<state>/<int:ID>", methods=['POST'])
@login_required
def admproximity(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('admproximity.html', ID = ID)
	elif state == 'check':
		emID = request.form['emID']
		proxID = request.form['ID']
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']

		DB = 'databases/emdatabases/%s.db' % (emID)
		# print(DB)

		if os.path.exists(DB) == False:
			templateData = {'Error': "ID Doesn't exists"}
			return render_template('admproximity.html', **templateData, ID = ID)

		try:
			conn = sqlite3.connect(DB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('admproximity.html', **templateData, ID = ID)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()

		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass
		if proxID != '':
			filters += " AND ID = '%s'" % (proxID)
		
		print(filters)
		try:
			cur.execute("SELECT * FROM Proximity %s" % (filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('admproximity.html', ID = ID, rows = rows)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('admproximity.html', ID = ID, **templateData)

@app.route("/admdash/canteen/<state>/<int:ID>", methods=['POST'])
@login_required
def admcanteen(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('admcanteen.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(canteenDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('admcanteen.html', **templateData, ID = ID)
		conn.row_factory = sqlite3.Row
		cur = conn.cursor()
		emID = request.form['emID']
		StartDate = request.form['StartDate']
		EndDate = request.form['EndDate']
		# print("%s %s %s" %(SELECT,StartDate, EndDate))
		filters = ''
		try:
			t = dt.datetime.strptime(StartDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND date('now')" % (StartDate)
			t = dt.datetime.strptime(EndDate, '%Y-%m-%d')
			filters = "WHERE date(TIMESTAMP) BETWEEN '%s' AND '%s'" % (StartDate, EndDate)
		except:      
			pass

		if emID != '':
			if filters == '':
				filters = "WHERE ID = '%s'" % (emID)
			else:
				filters += " AND ID = '%s'" % (emID)
		
		print(filters)
		try:
			cur.execute("SELECT * FROM Transactions %s" % (filters))
			rows = cur.fetchall()
			conn.close()
			return render_template('admcanteen.html', ID = ID, rows = rows)
		except:
			conn.close()
			templateData = {'Error': 'Nothing to show!'}
			return render_template('admcanteen.html', ID = ID, **templateData)			

@app.route("/admdash/emaddnew/<state>/<int:ID>", methods=['POST'])
@login_required
def emaddnew(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('emaddnew.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(mainDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('emaddnew.html', **templateData, ID = ID)

		NewName = request.form['NewName']
		NewRFID = request.form['NewRFID']
		NewPin = request.form['NewPin']

		cur = conn.cursor()
		try:
			cur.execute("SELECT RFID FROM EmList WHERE RFID = '%s'" %(NewRFID))
			checkRFID = cur.fetchone()[0]
		except:
			checkRFID = ''
		if checkRFID != '':
			templateData = {'Error': 'RFID Already Exists!'}
			conn.close()
			return render_template('emaddnew.html', **templateData, ID = ID)
		else:
			cur.execute("SELECT max(ID) FROM EmList")
			lastID = str(cur.fetchone()[0])
			DT = dt.datetime.now()
			lastIDyear = lastID[0:4]

			if lastIDyear != str(DT.year):
				NewID = int("%s0000"%(DT.year)) + 1
			else:
				NewID = int(lastID) +1

		cur.execute("INSERT INTO EmList VALUES (%d,'%s',%s,%s,-1,0,0);"%(NewID,NewName,NewRFID,NewPin))
		conn.commit()
		cur.execute("SELECT * FROM EmList WHERE ID = '%d'" %(NewID))
		newItem = cur.fetchone()
		conn.close()
		DB = 'databases/emdatabases/%d.db' %(NewID)
		conn = sqlite3.connect(DB)
		conn.execute('''CREATE TABLE Proximity(TIMESTAMP TEXT PRIMARY KEY NOT NULL, ID INT NOT NULL, NAME TEXT NOT NULL)''')
		conn.commit()
		conn.execute('''CREATE TABLE SensorRead(TIMESTAMP TEXT PRIMARY KEY NOT NULL, SPO2 INT NOT NULL, TEMPERATURE INT NOT NULL)''')
		conn.commit()
		conn.execute('''CREATE TABLE wearableList(ID INT PRIMARY KEY NOT NULL, RSSI INT NOT NULL)''')
		conn.commit()
		conn.close()
		templateData = {'Error': newItem}
		return render_template('emaddnew.html', **templateData, ID = ID)

@app.route("/admdash/emupdate/<state>/<int:ID>", methods=['POST'])
@login_required
def emupdate(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('emupdate.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(mainDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('emupdate.html', **templateData, ID = ID)

		emID = request.form['emID']
		toupdate = request.form['toupdate']
		valueupdate = request.form['valueupdate']

		cur = conn.cursor()
		cur.execute("SELECT * FROM EmList WHERE ID = %s" %(emID))
		if cur.fetchone() == None:
			conn.close()
			templateData = {'Error': 'ID not found!'}
			return render_template('emupdate.html', **templateData, ID = ID)
		if toupdate == 'null':
			conn.close()
			templateData = {'Error': 'Please select a value to update'}
			return render_template('emupdate.html', **templateData, ID = ID)
		else:
			try:
				cur.execute("UPDATE EmList SET %s = '%s' WHERE ID = %s" %(toupdate, valueupdate,emID))
				if toupdate == 'BLOCKED' and valueupdate == '0':
					cur.execute("UPDATE EmList SET NoofTry = 0 WHERE ID = %s" %(emID))
				elif toupdate == 'PIN':
					cur.execute("UPDATE EmList SET NoofTry = -1 WHERE ID = %s" %(emID))
				conn.commit()
				conn.close()
				templateData = {'Error': 'Success!'}
				return render_template('emupdate.html', **templateData, ID = ID)
			except:
				templateDate = {'Error': 'Enter valid value'}
				return render_template('emupdate.html', **templateData, ID = ID)

@app.route("/admdash/caddnew/<state>/<int:ID>", methods=['POST'])
@login_required
def caddnew(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('caddnew.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(canteenDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('caddnew.html', **templateData, ID = ID)

		NewItem = request.form['NewItem']
		NewPrice = request.form['NewPrice']

		cur = conn.cursor()
		try:
			cur.execute("SELECT NAME FROM ProductList WHERE NAME = '%s'" %(NewItem))
			checkItem = cur.fetchone()[0]
		except:
			checkItem = ''

		if checkItem != '':
			templateData = {'Error': 'Product Already Exists!'}
			conn.close()
			return render_template('caddnew.html', **templateData, ID = ID)

		cur.execute("INSERT INTO ProductList VALUES ('%s',%s);"%(NewItem,NewPrice))
		conn.commit()
		cur.execute("SELECT * FROM ProductList WHERE NAME = '%s'" %(NewItem))
		newItem = cur.fetchone()
		templateData = {'Error': newItem}
		conn.close()
		return render_template('caddnew.html', **templateData, ID = ID)

@app.route("/admdash/cupdate/<state>/<int:ID>", methods=['POST'])
@login_required
def cupdate(state, ID):
	curUsrID = current_user.get_id()
	if int(curUsrID) != ID:
		logout_user()
		return redirect(url_for('index'))
	if state == 'null':
		return render_template('cupdate.html', ID = ID)
	elif state == 'check':
		try:
			conn = sqlite3.connect(canteenDB)
		except:
			templateData = {'Error': "DataBase Busy! Try in a few"}
			return render_template('cupdate.html', **templateData, ID = ID)

		UpdateItem = request.form['UpdateItem']
		UpdatePrice = request.form['UpdatePrice']

		cur = conn.cursor()
		cur.execute("SELECT * FROM ProductList WHERE NAME = '%s'" %(UpdateItem))
		if cur.fetchone() == None:
			conn.close()
			templateData = {'Error': 'Item not found!'}
			return render_template('cupdate.html', **templateData, ID = ID)
		if int(UpdatePrice) == 0:
			cur.execute("DELETE FROM ProductList WHERE NAME = '%s'" %(UpdateItem))
			conn.commit()
			conn.close()
			templateData = {'Error': 'Product Deleted'}
			return render_template('cupdate.html', **templateData, ID = ID)
		else:
			cur.execute("UPDATE ProductList SET Price = %s WHERE NAME = '%s'" %(UpdatePrice, UpdateItem))
			conn.commit()
			conn.close()
			templateData = {'Error': 'Product Updated'}
			return render_template('cupdate.html', **templateData, ID = ID)

@app.route("/admdash/logout", methods=['POST'])
@login_required
def admlogout():
    logout_user()
    return redirect(url_for('index'))			

app.run(host='192.168.29.212', port= 8090, debug=True)