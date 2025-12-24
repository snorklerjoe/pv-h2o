/*
  Software to control our homemade Arduino-powered DC ground fault system.
  Written by Joseph R. Freeston, hardware by Andrew K. Freeston, 2020.
*/

#include "Arduino.h"
#include <avr/wdt.h>
#include <EEPROM.h>
#include "queue.h"  // From https://github.com/clnhlzmn/utils/tree/master/queue
#include "control.h"

#define BUFLEN 64  // Length of the buffer to store previous readings in.

// Address in the EEPROM of the tripping point in mA
#define EEPROM_ADDR_TRIP_MA 03

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
double offset1 = 0;
double offset2 = 0;

String cmdread;

bool C1_suspect, C2_suspect;
int C1_buflen, C2_buflen;

volatile int dump(volatile double *value, volatile void *ctx) {
  Serial.println(*value);
  return 0;
}

void runcmd() {
  if(Serial.available()>3) {
    wdt_disable();
    cmdread = Serial.readString();
    cmdread.trim();
    if(cmdread == "D_Q") {
      Serial.println("Circuit #1:");
      queue_buffer_foreach(&circuit1_readings, dump, &i);  // Dump the contents of the queue to the serial terminal
      Serial.println("Circuit #2:");
      queue_buffer_foreach(&circuit2_readings, dump, &i);  // Dump the contents of the queue to the serial terminal
    }
    else if(cmdread == "RST") {
      reboot();
    }
    else if(cmdread == "HLP" || cmdread == "???") {
      Serial.println("Commands:");
      Serial.println("RST            Resets the microcontroller");
      Serial.println("D_Q       Dump the last several current difference measurements");
      Serial.println("S_T      Type this, and then send a number, the milliamps to trip at (considering noise)");
      Serial.println("G_T      Shows current threshold");

      Serial.println("ST1             Gets Ch1 Status");
      Serial.println("ST2             Gets Ch2 Status");


      Serial.println("ON1               Turns on Ch 1");
      Serial.println("OF1              Turns on Ch 1");
      Serial.println("ON2               Turns on Ch 2");
      Serial.println("OF2              Turns on Ch 2");
    }
    else if(cmdread == "S_T") {
      while(!Serial.available()){delay(10);}
      delay(500);
      int new_thresh = Serial.readString().toInt();
      EEPROM.put(EEPROM_ADDR_TRIP_MA, new_thresh);
      int read_back;
      EEPROM.get(EEPROM_ADDR_TRIP_MA, read_back);
      Serial.println("OK, set EEPROM value to "+String(read_back));
    }
    // else if(cmdread == "SET_THRESH2") {
    //   while(!Serial.available()){}
    //   EEPROM.update(1, Serial.readString().toInt());
    //   Serial.println("Okay, set loc 1 to "+String(EEPROM.read(1)));
    // }
    else if(cmdread == "G_T") {
      int read_back;
      EEPROM.get(EEPROM_ADDR_TRIP_MA, read_back);
      Serial.println(String(read_back));
    }
    else if(cmdread == "ST1") {
      Serial.println(panel.get_status(CIRC_NUM1)==STAT_OK ? "OK" : "TRIPPED");
    }
    else if(cmdread == "ST2") {
      Serial.println(panel.get_status(CIRC_NUM2)==STAT_OK ? "OK" : "TRIPPED");
    }
    else if(cmdread == "ON1") {
      panel.turn_on(CIRC_NUM1);
      Serial.println("OK");
    }
    else if(cmdread == "ON2") {
      panel.turn_on(CIRC_NUM2);
      Serial.println("OK");
    }
    else if(cmdread == "OFF1") {
      panel.turn_off(CIRC_NUM1);
      Serial.println("OK");
    }
    else if(cmdread == "OFF2") {
      panel.turn_off(CIRC_NUM2);
      Serial.println("OK");
    }
    // else if(cmdread == "GET_THRESH2") {
    //   Serial.println(String(EEPROM.read(1)));
    // }
    else {
      Serial.println("Invalid command. type 'HLP' for help.");
    }
    wdt_enable(WDTO_500MS);
  }
}

void pushPt() {
  buf = abs((panel.get_current(0)-panel.get_current(1)) - offset1);
  queue_buffer_push(&circuit1_readings, &buf);
  buf = abs((panel.get_current(2)-panel.get_current(3)) - offset2);
  queue_buffer_push(&circuit2_readings, &buf);
}

void setup() {
  wdt_disable();
  wdt_reset();
  wdt_enable(WDTO_500MS);
  wdt_reset();
  Serial.begin(9600);
  Serial.setTimeout(5);
  panel.init();
  wdt_reset();
  //while(1) {
  //  Serial.println(panel.get_current(0));
  //}

  queue_buffer_init(&circuit1_readings);
  queue_buffer_init(&circuit2_readings);

  // Calibrate offsets
  Serial.println("Calibrating sensor offsets...");
  double sum1 = 0;
  double sum2 = 0;
  int cal_samples = 100;
  for(int i=0; i<cal_samples; i++) {
    sum1 += (panel.get_current(0) - panel.get_current(1));
    sum2 += (panel.get_current(2) - panel.get_current(3));
    delay(5);
    wdt_reset();
  }
  offset1 = sum1 / cal_samples;
  offset2 = sum2 / cal_samples;
  Serial.print("Offset 1: "); Serial.println(offset1);
  Serial.print("Offset 2: "); Serial.println(offset2);

  // Populate the currentReadings buffers while everything is off:
  Serial.println("Populating average buffers...");
  for(int i=0; i < BUFLEN; i++){
    pushPt();
    delay(1);
    wdt_reset();
  }
  C1_buflen = BUFLEN;
  C2_buflen = BUFLEN;
  Serial.println("Reading saved threshold value...");
  EEPROM.get(EEPROM_ADDR_TRIP_MA, thresh_bad);
  if (thresh_bad < 0 || thresh_bad > 10000) {
      thresh_bad = 200; // Default if EEPROM is invalid
  }
  Serial.println(String(thresh_bad));
  Serial.println("Powering up...");

  C1_suspect = false;
  C2_suspect = false;

  // Turn on both circuits:
  panel.set_status(CIRC_NUM1, STAT_OK);
  panel.set_status(CIRC_NUM2, STAT_OK);

  panel.turn_on(CIRC_NUM1);
  panel.turn_on(CIRC_NUM2);

  Serial.println("Ready.");
}

void loop() {
  wdt_reset();

  // Deal with any serial commands if available:
  runcmd();
  
  panel.loop();
  
  // Detect ground faults:

  queue_buffer_pop(&circuit1_readings, &buf);
  queue_buffer_pop(&circuit2_readings, &buf);
  C1_buflen = min(BUFLEN, C1_buflen + 1);
  C2_buflen = min(BUFLEN, C2_buflen + 1);
  pushPt();
  wdt_reset();
  delay(1);
  wdt_reset();

  // Should Circuit #1 Trip?
  if(C1_buflen == BUFLEN && panel.get_status(CIRC_NUM1) == STAT_OK) {  // If we have data AND aren't already tripped
    // Get the current rolling average of delta in current:
    // queue_buffer_foreach(&circuit1_readings, total, &i);  // Get the total (previous samples)
    avgbuf = queue_buffer_doublesum(&circuit1_readings);
    avgbuf /= BUFLEN;                                     // Calculate the average (of the previous samples)
    bool above_thresh = abs(avgbuf) > thresh_bad;

    if(C1_suspect) {  // If we were already suspecting a fault
      if(above_thresh) { // FAULT if suspected and measured
        panel.turn_off(CIRC_NUM1);
        panel.set_status(CIRC_NUM1, STAT_TRIPPED);
      } else C1_suspect = false;  // If no issue, clear the suspicion.
    } else {
      if(above_thresh) {  // Cause for concern. But maybe it's a glitch.
        // Flush the buffer and await its refilling
        C1_buflen = 0;
        C1_suspect = true;
      }  // Else, all is well!
    }
  }
  wdt_reset();
  // Should Circuit #2 Trip?
  if(C2_buflen == BUFLEN && panel.get_status(CIRC_NUM2) == STAT_OK) {  // If we have data AND aren't already tripped
    // Get the current rolling average of delta in current:
    avgbuf = queue_buffer_doublesum(&circuit2_readings);
    avgbuf /= BUFLEN;                                     // Calculate the average (of the previous samples)
    bool above_thresh = abs(avgbuf) > thresh_bad;

    if(C2_suspect) {  // If we were already suspecting a fault
      if(above_thresh) { // FAULT if suspected and measured
        panel.turn_off(CIRC_NUM2);
        panel.set_status(CIRC_NUM2, STAT_TRIPPED);
      } else C2_suspect = false;  // If no issue, clear the suspicion.
    } else {
      if(above_thresh) {  // Cause for concern. But maybe it's a glitch.
        // Flush the buffer and await its refilling
        C2_buflen = 0;
        C2_suspect = true;
      }  // Else, all is well!
    }
  }
}

void reboot() {
  wdt_disable();
  wdt_enable(WDTO_15MS);
  while (1) {}
}
