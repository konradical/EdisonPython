#!/usr/bin/python

from __future__ import absolute_import, print_function, unicode_literals

from optparse import OptionParser, make_option
import os
import sys
import socket
import uuid
import dbus
import dbus.service
import dbus.mainloop.glib
try:
  from gi.repository import GObject
except ImportError:
  import gobject as GObject

class Profile(dbus.service.Object):
	fd = -1
	execValues = {'rate': 100, 'time': 5, 'name': 'data'}
	cmd = '/home/root/mpu6500D -r 100 -t 5 -n data.txt'

	@dbus.service.method("org.bluez.Profile1",
					in_signature="", out_signature="")
	def Release(self):
		print("Release")
		mainloop.quit()

	@dbus.service.method("org.bluez.Profile1",
					in_signature="", out_signature="")
	def Cancel(self):
		print("Cancel")

	def printOptions(self, server_sock):
		server_sock.send("\n\nEnter letter command from options:\n"
				 "a - setup test\n"  
				 "c - change value\n"
				 "e - execute command (immediate start)\n"
				 "r - reboot\n"
				 "s - shutdown\n"
				 "t - transfer data\n")
	
	def createCmdString(self, test_num):
		print("creating command string\n")
		
		rate = self.execValues['rate'] 
		seconds = self.execValues['time']
		name = self.execValues['name']
		cmd = "/home/root/mpu6500D"
		cmd += " -r %d -t %d -n %s" % (rate,seconds,name)
		cmd += "-%dHz%ds#%d.txt" % (rate, seconds, test_num)
		
		print("%s\n" % cmd)
		print('woohoo')
		return cmd

	def askForInputs(self, socket):
		socket.send("\n\nSensor data collection: Begin user input\n")
                
		socket.send("\nInput rate? Enter 'no' or rate value in Hz\n")
                val = socket.recv(1024)                       
		socket.send("%s entered\n" % val)
                if (val[0]+val[1]) != 'no':
		    self.execValues['rate'] = self.evalInput('rate', val)

		socket.send("\nInput seconds? Enter 'no' or time value in seconds\n") 
       		val = socket.recv(1024)
		socket.send("%s entered\n" % val) 
		if (val[0]+val[1]) != 'no':
		    self.execValues['time'] = self.evalInput('time', val)
	
		socket.send("\nInput filename? Enter 'no' or filename\n")
		val = socket.recv(1024)
		socket.send("%s entered\n\n" % val) 
		if (val[0]+val[1]) != 'no':
                    self.execValues['name'] = self.evalInput('name', val)


	def evalInput(self,key,val):
		if (key == 'name'):
		    return val
		return eval(val)

	def printExecValues(self, sock):
                sock.send("rate (Hz) :\t %d\n" % self.execValues['rate'] +      
                          "time (sec):\t %d\n" % self.execValues['time'] +      
                          "name      :\t %s\n\n" % self.execValues['name']) 

	def confirmValues(self, sock):
		while(True):	
		    sock.send("\nAre these the values you want to test with?\n\n")
		    self.printExecValues(sock)
		    sock.send("Enter 'y' for yes or name of value to update.\n") 
		    choice = sock.recv(1024)						
                    successful = self.updateValue(sock, choice)

		    print('checkng for yes option')
		    if choice[0] == 'y': 
		        print('yes reached to break')
			break

		    if not successful:	
			sock.send("Invalid input. Try again.\n")

	def updateValue(self, sock, choice):
	    print('entering update loop check\n')                   
            for update in self.execValues:                          
                if (choice == update):                          
                    sock.send("\nEnter new %s\n" % choice) 
                    value = sock.recv(1024)                 
                    print("%s + %s" % (choice, value))      
                    self.changeValue(choice, value)         
                    sock.send("%s updated to: %s\n\n" % (choice, value))
		    return True

	def changeValue(self, key, value):
		self.execValues[key] = self.evalInput(key, value)
		print("%s successfully changed to %s" % (key, value))

	def ValueAndCmdSetup(self, test_num, sock):
		self.askForInputs(sock)             
                sock.send("Inputs Acquired\n")
		self.confirmValues(sock)      
                sock.send("Values confirmed.\n")             
		return self.createCmdString(test_num) 

	def waitForGo(self, sock):
            sock.send("\nWaiting for go command. (Send anything)\n")
	    sock.recv(10)
	    sock.send("Executing\n%s\n" % self.cmd)
            self.executeCmd()

	def executeCmd(self):
	    while True:
		print("%s" % self.cmd)
	     #  os.system("%s" % cmd)
		print('blah')
		break
		
	@dbus.service.method("org.bluez.Profile1",
				in_signature="oha{sv}", out_signature="")
	def NewConnection(self, path, fd, properties):
		self.fd = fd.take()
		print("NewConnection(%s, %d)" % (path, self.fd))

		server_sock = socket.fromfd(self.fd, socket.AF_UNIX, socket.SOCK_STREAM)
		server_sock.setblocking(1)
		server_sock.send("This is Edison SPP loopback test\nAll data will be loopback\nPlease start:\n")

		print("it worked")
		self.printOptions(server_sock)
		iterations = 0

		try:
		    while True:
		        data = server_sock.recv(1024)
    			
			if data[0] == 'a':
			    print("user setup\n")
			    iterations = iterations + 1
			    self.cmd = self.ValueAndCmdSetup(iterations, server_sock)
			    server_sock.send("\n Command set to:\n%s\n" % self.cmd)	
    			    self.waitForGo(server_sock)
			
			if data[0] == 'c':
			    print('change value\n')
			    server_sock.send("\nCurrent property values\n\n")
			    self.printExecValues(server_sock)
			    server_sock.send("\nWhich property do you want to change?"
					     " (Enter property name)\n")
			    name = server_sock.recv(1024)
			    self.updateValue(server_sock, name)	
	
			if data[0] == 'e':
			    print('entered e')
			    iterations = iterations + 1
			    self.cmd = self.createCmdString(iterations)
			    server_sock.send("\nExecuting command\n%s\n\n" % self.cmd)
			    self.executeCmd()

    			if data[0] == 't':
    				print("transfer data\n")
				server_sock.send("\nEnter name of session to store all data to\n")
    				filename = server_sock.recv(1024)
				filename += ".tar"
				os.system("tar -cvf %s *.txt" % filename)
				os.system("/usr/lib/bluez/test/ftp-client -d 80:E6:50:24:AD:6F -p %s" % filename)
                	
			if data[0] == 'r':
                    		print("rebooting...\n")
                    		os.system("reboot")

			if data[0] == 's':
  				print("shutting down\n")
				break

  			server_sock.send("looping back command: %s\n" % data)
			
			self.printOptions(server_sock)
		
		except IOError:
		    server_sock.send("error k-rad\n")
		    pass

		server_sock.close()
		print("all done")
		os.system("shutdown now")


	@dbus.service.method("org.bluez.Profile1",
				in_signature="o", out_signature="")
	def RequestDisconnection(self, path):
		print("RequestDisconnection(%s)" % (path))

		if (self.fd > 0):
			os.close(self.fd)
			self.fd = -1

if __name__ == '__main__':
#	os.system("rfkill unblock bluetooth")
#	os.system("export DBUS_SESSION_BUS_ADDRESS=unix:path=/var/run/dbus/system_bus_socket")
#	os.system("systemctl start obex")

	dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

	bus = dbus.SystemBus()

	manager = dbus.Interface(bus.get_object("org.bluez",
				"/org/bluez"), "org.bluez.ProfileManager1")

	option_list = [
			make_option("-C", "--channel", action="store",
					type="int", dest="channel",
					default=None),
			]

	parser = OptionParser(option_list=option_list)

	(options, args) = parser.parse_args()

	options.uuid = "1101"
	options.psm = "3"
	options.role = "server"
	options.name = "Edison SPP Loopback"
	options.service = "spp char loopback"
	options.path = "/foo/bar/profile"
	options.auto_connect = False
	options.record = ""

	profile = Profile(bus, options.path)

	mainloop = GObject.MainLoop()

	opts = {
			"AutoConnect" :	options.auto_connect,
		}

	if (options.name):
		opts["Name"] = options.name

	if (options.role):
		opts["Role"] = options.role

	if (options.psm is not None):
		opts["PSM"] = dbus.UInt16(options.psm)

	if (options.channel is not None):
		opts["Channel"] = dbus.UInt16(options.channel)

	if (options.record):
		opts["ServiceRecord"] = options.record

	if (options.service):
		opts["Service"] = options.service

	if not options.uuid:
		options.uuid = str(uuid.uuid4())

	manager.RegisterProfile(options.path, options.uuid, opts)

	mainloop.run()
