#include "oonf.h"

/*PUBLIC FUNCTIONS*/
/**
 * Initalize a new oonf plugin handler
 * @param host host address as a string
 * @return pointer to oonf plugin handler
 */
routing_plugin *new_plugin(char *host, int port, int json_type, int timer_port)
{
	routing_plugin *o = (routing_plugin *)malloc(sizeof(routing_plugin));
	if (o == NULL) {
		perror("oonf");
		exit(EXIT_FAILURE);
	}
	o->port = port;
	o->host = strdup(host);
	o->json_type = json_type;
	o->recv_buffer = NULL;
	o->self_id = NULL;
	o->timer_port = timer_port; // the port is the same for netjson topolgy
				    // and timer update
	return o;
}

/**
 * Delete the oonf plugin handler
 * @param oonf plugin handler object
 */
void delete_plugin(routing_plugin *o)
{
	if (o != NULL) {
		if (o->host != NULL) {
			free(o->host);
		}
		if (o->recv_buffer != NULL) {
			free(o->recv_buffer);
		}
		if (o->self_id != NULL) {
			free(o->self_id);
		}
		if (o->t != NULL) {
			free(o->t);
		}
		free(o);
	}
}

/**
 * Get the topology data from host
 * @param oonf plugin handler object
 * @return 0 if success, -1 otherwise
 */
int get_topology(routing_plugin *o)
{
	int sent;
	if ((o->sd = _create_socket(o->host, o->port, 0)) == 0) {
		printf("Cannot connect to %s:%d", o->host, o->port);
		return -1;
	}
	char *req = "/netjsoninfo filter graph ipv6_0/quit\n";
	printf("Sending message %s", req);
	if ((sent = send(o->sd, req, strlen(req), MSG_NOSIGNAL)) == -1) {
		printf("Cannot send to %s:%d", o->host, o->port);
		close(o->sd);
		return -1;
	}
	if (o->recv_buffer != NULL) {
		free(o->recv_buffer);
		o->recv_buffer = 0;
	}
	if (!_telnet_receive(o->sd, &(o->recv_buffer))) {
		printf("cannot receive \n");
		close(o->sd);
		return -1;
	}
	o->t = parse_netjson(o->recv_buffer);
	if (o->t == INVALID_TOPOLOGY) {
		fprintf(stderr, "Can't parse netjson\n");
		fprintf(stderr, "%s\n", o->recv_buffer);
		close(o->sd);
		return -1;
	}
	close(o->sd);
	return 0;
}


/**
 * Push the timers value to the routing daemon
 * @param oonf plugin handler object
 * @return 1 if success, 0 otherwise
 */
int push_timers(routing_plugin *o, struct timers t)
{
	o->sd = _create_socket(o->host, o->timer_port, 0);
	char cmd[111];
	sprintf(cmd, "/config remove olsrv2.tc_interval/config remove interface.hello_interval");
	write(o->sd, cmd, strlen(cmd));
	sprintf(cmd,
		"/config set olsrv2.tc_interval=%4.2f/config set interface.hello_interval=%4.2f/config commit/quit",
		t.tc_timer, t.h_timer);
	write(o->sd, cmd, strlen(cmd));
	printf("Pushed Timers %4.2f  %4.2f\n", t.tc_timer, t.h_timer);
	close(o->sd);
	return 1;
}


int get_initial_timers(routing_plugin *o, struct timers *t)
{
	t->h_timer = parse_initial_timer(o, HELLO_TIMER_MESSAGE);
	t->tc_timer = parse_initial_timer(o, TC_TIMER_MESSAGE);
	if (t->h_timer == -1) {
		fprintf(stderr, "Could not initialise h_timer\n");
		fprintf(stdout, "Setting h_timer to 2\n");
		t->h_timer = 2;
	}
	if (t->tc_timer == -1) {
		fprintf(stderr, "Could not initialise tc_timer\n");
		fprintf(stdout, "Setting tc_timer to 5\n");
		t->tc_timer = 5;
	}
	return 0;
}

float parse_initial_timer(routing_plugin *o, const char *cmd)
{
	o->sd = _create_socket(o->host, o->timer_port, ECONNREFUSED);
	char *page;
	char *token;
	float value = 0;
	page = (char *)malloc(RESPONSE_SIZE);
	if (page == NULL) {
		perror("olsr");
		return -1;
	}
	write(o->sd, cmd, strlen(cmd));
	if (recv(o->sd, page, RESPONSE_SIZE, 0) > 0) {
		token = strtok(page, "\n");
		token = strtok(NULL, "\n");
		value = atof(token);
	} else {
		fprintf(stderr, "Could not recieve timer %s\n", cmd);
		return -1;
	}
	close(o->sd);
	free(page);
	if (value == 0) {
		return -1;
	}
	return value;
}
