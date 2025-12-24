/*
  Software to control our homemade Arduino-powered DC ground fault system.
  Written by Joseph R. Freeston, hardware by Andrew K. Freeston, 2020.
*/

#include "Arduino.h"
#include <avr/wdt.h>
#include <EEPROM.h>
#include "queue.h"  // From https://github.com/clnhlzmn/utils/tree/master/queue
#include "control.h"

#define BUFLEN 32  // Length of the buffer to store previous readings in.

Panel panel;

//int currentReadings1[BUFLEN];
//int currentReadings2[BUFLEN];

QUEUE(buffer, double, BUFLEN);

volatile struct queue_buffer circuit1_readings;
volatile struct queue_buffer circuit2_readings;

int thresh_bad = 200;      // # of mA difference to make it trip. This is not instant, as it should remove outliers, see the next line also.
int thresh_realbad = 1000; // # of mA difference to make it trip instantly. This should be much higher than the noise floor, as it will not check for outliers.

int i;

double buf, avgbuf;

String cmdread;

int total(double *value) {
  avgbuf += *value;
  return 0;
}

int dump(double *value) {
  Serial.println(*value);
  return 0;
}

void runcmd() {
  if(Serial.available()) {
    cmdread = Serial.readString();
    if(cmdread == "DUMP_QUEUE") {
      Serial.println("Circuit #1:");
      queue_buffer_foreach(&circuit1_readings, dump, &i);  // Dump the contents of the queue to the serial terminal
      Serial.println("Circuit #2:");
      queue_buffer_foreach(&circuit2_readings, dump, &i);  // Dump the contents of the queue to the serial terminal
    }
    else if(cmdread == "RESET") {
      reboot();
    }
    else if(cmdread == "HELP") {
      Serial.println("Commands:");
      Serial.println("RESET            Resets the microcontroller");
      Serial.println("DUMP_QUEUE       Dump the last several current difference measurements");
      Serial.println("SET_THRESH1      Type this, and then send a number, the milliamps to trip at (considering noise) / 10");
      Serial.println("SET_THRESH2      Sets the # of milliamps to trip at immediately no matter what (without the sliding average)");
      Serial.println("GET_THRESH1      Opposite of SET_THRESH1");
      Serial.println("GET_THRESH2      Opposite of SET_THRESH2");
    }
    else if(cmdread == "SET_THRESH1") {
      while(!Serial.available()){}
      EEPROM.update(0, Serial.readString().toInt());
      Serial.println("Okay, set loc 0 to "+String(EEPROM.read(0)));
    }
    else if(cmdread == "SET_THRESH2") {
      while(!Serial.available()){}
      EEPROM.update(1, Serial.readString().toInt());
      Serial.println("Okay, set loc 1 to "+String(EEPROM.read(1)));
    }
    else if(cmdread == "GET_THRESH1") {
      Serial.println(String(EEPROM.read(0)));
    }
    else if(cmdread == "GET_THRESH2") {
      Serial.println(String(EEPROM.read(1)));
    }
    else {
      Serial.println("Invalid command. type 'HELP' for help.");
    }
  }
}

void setup() {
  Serial.begin(9600);
  Serial.setTimeout(5);
  panel.init();
  //while(1) {
  //  Serial.println(panel.get_current(0));
  //}

  queue_buffer_init(&circuit1_readings);
  queue_buffer_init(&circuit2_readings);

  // Populate the currentReadings buffers while everything is off:
  Serial.println("Populating average buffers...");
  for(int i=0; i < BUFLEN; i++){
    buf = abs(panel.get_current(0)-panel.get_current(1));
    queue_buffer_push(&circuit1_readings, &buf);
    buf = abs(panel.get_current(2)-panel.get_current(3));
    queue_buffer_push(&circuit2_readings, &buf);
    delay(1);
  }
  Serial.println("Reading saved threshold values...");
  thresh_bad = EEPROM.read(0)*10;
  thresh_realbad = EEPROM.read(1)*10;
  Serial.println(String(thresh_bad)+", "+String(thresh_realbad));
  Serial.println("Powering up...");

  // Turn on both circuits:
  panel.set_status(CIRC_NUM1, STAT_OK);
  panel.set_status(CIRC_NUM2, STAT_OK);

  panel.turn_on(CIRC_NUM1);
  panel.turn_on(CIRC_NUM2);

  Serial.println("Ready.");
}

void loop() {
  runcmd();
  
  panel.loop();
  
  // Detect ground faults:
  //WARNING: CIRCUIT 2 is not yet protected.

  queue_buffer_pop(&circuit1_readings, &buf);
  queue_buffer_pop(&circuit2_readings, &buf);


  // Circuit #1:
  if(panel.get_status(CIRC_NUM1) == STAT_OK){
    queue_buffer_foreach(&circuit1_readings, total, &i);  // Get the total (previous samples)
    avgbuf /= BUFLEN;                                     // Calculate the average (of the previous samples)
    
    buf = abs(panel.get_current(0)-panel.get_current(1)); // Take another sample
  
    if((buf > thresh_realbad) or (avgbuf > thresh_bad)) { // AAAAH!!! If this is true, we have a ground fault (or a glitch).
      panel.turn_off(CIRC_NUM1);                          // Immediately turn off circuit #1
      Serial.println("GROUND FAULT on CIRCUIT #1!");
      delay(5);
      buf = abs(panel.get_current(0)-panel.get_current(1));  // Check to see if we fixed it...
      if((buf > thresh_realbad) or (avgbuf > thresh_bad)) {
        panel.turn_off(CIRC_NUM1);                        // Redundant, but just in case.
        Serial.println("The issue has not been removed after 5 ms");
      }
      delay(10);
      buf = abs(panel.get_current(0)-panel.get_current(1));  // Make sure we fixed it...
      if((buf > thresh_realbad) or (avgbuf > thresh_bad)) {
        Serial.println("THE FAULT HAS NOT BEEN REMOVED AFTER 15 MS!");
        panel.set_status(CIRC_NUM1, STAT_FAULT);
        panel.turn_off(CIRC_NUM1);
        panel.turn_off(CIRC_NUM2);
        Serial.println("Powered off both circuits.\nDumping queue:");
        queue_buffer_foreach(&circuit1_readings, dump, &i);  // Dump the contents of the queue to the serial terminal
        Serial.println("\n\n__ENTERING EMERGENCY MODE__");
        while(1){
          runcmd();
          delay(50);
          panel.loop();
        }
      }
      Serial.println("The issue has been fixed.\nCircuit #1 will remain tripped until a reset.");
      panel.set_status(CIRC_NUM1, STAT_TRIPPED);
    }
    else {
      queue_buffer_push(&circuit1_readings, &buf);
    }
  }
  
  // Circuit #2
  if(panel.get_status(CIRC_NUM2) == STAT_OK){
    queue_buffer_foreach(&circuit2_readings, total, &i);  // Get the total (previous samples)
    avgbuf /= BUFLEN;                                     // Calculate the average (of the previous samples)
    
    buf = abs(panel.get_current(2)-panel.get_current(3)); // Take another sample
  
    if((buf > thresh_realbad) or (avgbuf > thresh_bad)) { // AAAAH!!! If this is true, we have a ground fault (or a glitch).
      panel.turn_off(CIRC_NUM2);                          // Immediately turn off circuit #1
      Serial.println("GROUND FAULT on CIRCUIT #2!");
      delay(5);
      buf = abs(panel.get_current(2)-panel.get_current(3));  // Check to see if we fixed it...
      if((buf > thresh_realbad) or (avgbuf > thresh_bad)) {
        panel.turn_off(CIRC_NUM2);                        // Redundant, but just in case.
        Serial.println("The issue has not been removed after 5 ms");
      }
      delay(10);
      buf = abs(panel.get_current(2)-panel.get_current(3));  // Make sure we fixed it...
      if((buf > thresh_realbad) or (avgbuf > thresh_bad)) {
        Serial.println("THE FAULT HAS NOT BEEN REMOVED AFTER 15 MS!");
        panel.set_status(CIRC_NUM2, STAT_FAULT);
        panel.turn_off(CIRC_NUM1);
        panel.turn_off(CIRC_NUM2);
        Serial.println("Powered off both circuits.\nDumping queue:");
        queue_buffer_foreach(&circuit2_readings, dump, &i);  // Dump the contents of the queue to the serial terminal
        Serial.println("\n\n__ENTERING EMERGENCY MODE__");
        while(1){
          runcmd();
          delay(50);
          panel.loop();
        }
      }
      Serial.println("The issue has been fixed.\nCircuit #1 will remain tripped until a reset.");
      panel.set_status(CIRC_NUM2, STAT_TRIPPED);
    }
    else {
      queue_buffer_push(&circuit2_readings, &buf);
    }
  }
}

void reboot() {
  wdt_disable();
  wdt_enable(WDTO_15MS);
  while (1) {}
}
