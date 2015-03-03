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

import networkx as nx
import matplotlib.pyplot as plt
import random
import dbus

if __name__ == "__main__":
	G = nx.Graph()

	bus = dbus.SessionBus()
	tracker = bus.get_object('org.freedesktop.Tracker1', '/org/freedesktop/Tracker1/Resources')
	dbusclient = dbus.Interface(tracker, dbus_interface='org.freedesktop.Tracker1.Resources')

	query = "SELECT ?e WHERE {?e a nmo:Email}"
	mails = dbusclient.SparqlQuery(query)
	for mail in mails:
		uri = mail[0]
		group = []

		query = "SELECT ?c WHERE {{ <{uri}> nmo:to ?c }}".format(uri = uri)
		contacts = dbusclient.SparqlQuery(query)
		for contact in contacts:
			c = contact[0]
			group.append(c)

		query = "SELECT ?c WHERE {{ <{uri}> nmo:from ?c }}".format(uri = uri)
		contacts = dbusclient.SparqlQuery(query)
		for contact in contacts:
			c = contact[0]
			group.append(c)

		query = "SELECT ?c WHERE {{ <{uri}> nmo:cc ?c }}".format(uri = uri)
		contacts = dbusclient.SparqlQuery(query)
		for contact in contacts:
			c = contact[0]
			group.append(c)

		G.add_nodes_from(group)

		for top in group:
			for down in group:
				# Add this condition to skip direct connections if one already exists
				# if not nx.has_path(G, top, down):
				G.add_edge(top, down)

	print "Data collected, now rendering... Be patient..."

	# Visualization example got from
	# http://networkx.lanl.gov/examples/drawing/atlas.html
	plt.figure(figsize=(40, 40))
	pos = nx.graphviz_layout(G, prog="neato")
	C = nx.connected_component_subgraphs(G)
	for g in C:
		# This is to get rid of useless sub-graphs (e.g. spare spammy mails with me in BCC)
		tot = nx.number_of_nodes(g)
		if tot < 20:
			continue

		c = [random.random()] * tot
		nx.draw(g, pos, node_size=20, node_color=c, vmin=0.0, vmax=1.0, with_labels=False)
	plt.savefig("/tmp/contacts.png")
