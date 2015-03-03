#!/usr/bin/env python
#
# Copyright (C) 2015 Roberto -MadBob- Guido <bob@linux.it>
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# For references:
# https://wiki.gnome.org/Projects/Tracker/Documentation/Examples/SPARQL/Email

import re
import time
import datetime
import email
import imaplib
import uuid
import dbus

def parseReplyTo(contents):
	global messages

	messageid = contents.get('In-Reply-To')
	if messages.has_key (messageid):
		return 'nmo:inReplyTo <' + messages[messageid] + '>;'
	else:
		return ''

def executeQuery(query):
	global dbusclient

	try:
		dbusclient.SparqlUpdate(query)
	except dbus.exceptions.DBusException as e:
		print query
		time.sleep(5)
		dbusclient.SparqlUpdate(query)

def parseAddresses(contents, index, attribute, once):
	global contacts

	ret = ''
	pattern = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

	addresses = email.utils.getaddresses (contents.get_all(index, []))
	for addr in addresses:
		name = addr[0]
		mail = addr[1]

		if name != '':
			name = name.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

		if not re.match(pattern, mail):
			continue

		if not contacts.has_key (mail):
			if name == '':
				convertedname = uuid.uuid1()
			else:
				convertedname = name.lower().encode('ascii', 'ignore').translate (None, ''.join([' ', '<', '>', ':', '.', '(', ')', '{', '}', '[', ']', '?', '^', '|', "'", '"', '`', '\\']))

			uri = '<urn:contact:{}>'.format(convertedname)

			# Just to avoid conflicts with existing contacts
			query = 'DELETE WHERE {{ {uri} nco:fullname ?n }}'.format(uri = uri)
			executeQuery(query)

			query = "INSERT {{ <mailto:{mail}> a nco:EmailAddress; nco:emailAddress '{mail}' . \
				{uri} a nco:Contact; nco:hasEmailAddress <mailto:{mail}>; nco:fullname '{name}' }}".format(mail = mail, uri = uri, name = name)

			executeQuery(query)
			contacts[mail] = uri

		ret += attribute + ' ' + contacts[mail] + '; '
		if once == True:
			break

	return ret

def index_message(uri, contents):
	global messages

	stamp = time.mktime(email.utils.parsedate (contents.get('Date')))
	datet = datetime.datetime.fromtimestamp(stamp)
	date = datet.isoformat()

	subject = contents.get('Subject')
	if subject != None:
		subject = subject.replace('\\', '\\\\').replace("'", "\\'").replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')
	else:
		subject = ''

	fromaddr = parseAddresses (contents, 'From', 'nmo:from', True)
	toaddr = parseAddresses (contents, 'To', 'nmo:to', False)
	ccaddr = parseAddresses (contents, 'CC', 'nmo:cc', False)

	messageid = contents.get('Message-ID')
	replyto = parseReplyTo (contents)

	query = "INSERT {{ <{uri}> a nmo:Email, nmo:MailboxDataObject; \
		{toaddr} {fromaddr} {ccaddr} \
		nmo:messageSubject '{subject}'; \
		nmo:messageId '{messageid}'; {replyto} \
		nmo:sentDate '{date}'; \
		nie:isStoredAs <{uri}>; \
		nie:url '{uri}' }}".format(uri = uri, toaddr = toaddr, fromaddr = fromaddr, ccaddr = ccaddr, messageid = messageid, replyto = replyto, subject = subject, date = date)

	messages [messageid] = uri
	executeQuery(query)

if __name__ == "__main__":
	global messages, contacts, dbusclient

	# Tested only on GMail. In "username" you have to put your mail address (e.g. foobar@gmail.com)
	host = 'imap.gmail.com'
	username = 'YOUR_MAIL_ADDRESS'
	password = 'YOUR_PASSWORD'

	bus = dbus.SessionBus()
	tracker = bus.get_object('org.freedesktop.Tracker1', '/org/freedesktop/Tracker1/Resources')
	dbusclient = dbus.Interface(tracker, dbus_interface='org.freedesktop.Tracker1.Resources')

	datetime.microsecond = 0
	messages = {}
	contacts = {}

	mail = imaplib.IMAP4_SSL(host)
	mail.login(username, password)
	mail.list()
	mail.select("inbox")

	command = "ALL"
	result, data = mail.uid('search', None, command)
	uids = data[0].split()

	index = 0
	done = {}

	for message_uid in uids:
		while done.has_key(message_uid):
			message_uid += 1

		uri = 'imap://' + username + '/INBOX/;uid=' + message_uid

		# This is to fetch all contents of the message
		# result, data = mail.uid('fetch', message_uid, '(RFC822)')
		result, data = mail.uid('fetch', message_uid, '(BODY.PEEK[HEADER])')

		raw_email = data[0][1]
		email_message = email.message_from_string(raw_email)
		index_message(uri, email_message)

		done[message_uid] = True

		index += 1
		if index % 100 == 0:
			print index
