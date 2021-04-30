#include <mosquitto.h>
#include <stdio.h>


int main(int argc, char *argv[])
{
	struct mosquitto *mosq;
	int rc;

	mosquitto_lib_init();
	mosq = mosquitto_new(NULL, true, NULL);
	if(mosq == NULL){
		fprintf(stderr, "Error: Out of memory.\n");
		return 1;
	}
	printf("create mosquitto instance : %p\n", mosq);
	mosquitto_lib_cleanup();
	printf("mosquitto instance cleanup done.\n");
	return 0;
}

