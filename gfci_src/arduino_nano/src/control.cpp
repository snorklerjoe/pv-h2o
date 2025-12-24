/* 
  Control.cpp - Library for controlling our homemade solar DC ground fault system.
  Written by Joseph R. Freeston, hardware by Andrew K. Freeston, 2020.
*/

#include "Arduino.h"
#include "HardwareSerial.h"
#include "control.h"

void Panel::init() {
  Serial.println("Initializing DC ground fault system...");
  pinMode(7, OUTPUT);
  pinMode(2, OUTPUT);
  pinMode(3, OUTPUT);
  pinMode(4, OUTPUT);
  turn_off(CIRC_NUM1);
  turn_off(CIRC_NUM2);

  pinMode(_LED_1_1, OUTPUT);
  pinMode(_LED_1_2, OUTPUT);
  pinMode(_LED_2_1, OUTPUT);
  pinMode(_LED_2_2, OUTPUT);
  _blinky();
  _tmpbuf1 = false;
  _tmpbuf2 = true;
}

void Panel::_blinky() {  // An aesthetically pleasing display for initialization
  digitalWrite(_LED_1_1, true);
  digitalWrite(_LED_1_2, true);
  digitalWrite(_LED_2_1, true);
  digitalWrite(_LED_2_2, true);
  delay(50);
  digitalWrite(_LED_2_2, false);  
  delay(50);
  digitalWrite(_LED_2_1, false);  
  delay(50);
  digitalWrite(_LED_1_2, false);  
  delay(50);
  digitalWrite(_LED_1_1, false);
  delay(150);
}

void Panel::_alert(String text){
  Serial.println("ALERT: "+text);
  delay(500);
}

void Panel::_note(String text){
  Serial.println("NOTE: "+text);
}

void Panel::turn_on(int circuit){
  if(circuit == CIRC_NUM1){
    digitalWrite(7, true);
    digitalWrite(2, true);
  }
  else if(circuit == CIRC_NUM2){
    digitalWrite(3, true);
    digitalWrite(4, true);
  }
  else {
    _alert("Invalid circuit specified for turn_on!");
  }
}

void Panel::turn_off(int circuit){
  if(circuit == CIRC_NUM1){
    digitalWrite(7, false);
    digitalWrite(2, false);
  }
  else if(circuit == CIRC_NUM2){
    digitalWrite(3, false);
    digitalWrite(4, false);
  }
  else {
    _alert("Invalid circuit specified for turn_off!");
  }
}

void Panel::set_status(int circuit, Status stat) {
  if(circuit == CIRC_NUM1){
    _note("-- Setting status1 to 0x0"+String(stat));
    _status1 = stat;  // Record the status
    // Display the status:
    if(stat == STAT_OK){
      digitalWrite(_LED_1_1, false);  // Common anode, so active low.
      digitalWrite(_LED_1_2, true);
    }
    else if(stat == STAT_TRIPPED or stat == STAT_FAULT){
      digitalWrite(_LED_1_1, true);
      digitalWrite(_LED_1_2, false);
    }
  }
  else if(circuit == CIRC_NUM2){
    _note("-- Setting status2 to 0x0"+String(stat));
    _status2 = stat;  // Record the status
    // Display the status:
    if(stat == STAT_OK){
      digitalWrite(_LED_2_1, false);
      digitalWrite(_LED_2_2, true);
    }
    else if(stat == STAT_TRIPPED or stat == STAT_FAULT){
      digitalWrite(_LED_2_1, true);
      digitalWrite(_LED_2_2, false);
    }  }
  else {
    _alert("Invalid circuit specified for set_status!");
  }
}

Status Panel::get_status(int circuit) {
  if(circuit == CIRC_NUM1){
    return _status1;
  }
  else if(circuit == CIRC_NUM2){
    return _status2;
  }
  else {
    _alert("Invalid circuit specified for get_status!");
  }
}

double Panel::get_current(int sensor) {
  double tmpbuf = analogRead(sensor)*50000.0/1023.0;
  // delay(1);
  double tmpbuf2 = analogRead(sensor)*50000.0/1023.0;
  // if(abs(tmpbuf-tmpbuf2) > 100) {  // If we think that one of them is bogus, redo both
    // tmpbuf = analogRead(sensor)*50000/1023;
    // tmpbuf2 = analogRead(sensor)*50000/1023;
  // }
  tmpbuf += tmpbuf2;
  tmpbuf /= 2;
  return tmpbuf;
}

void Panel::loop() {
  if(_status1 == STAT_FAULT or _status2 == STAT_FAULT){
    _tmpbuf1 = !_tmpbuf1;
    digitalWrite(_LED_1_2, _tmpbuf1);
    _tmpbuf2 = !_tmpbuf2;
    digitalWrite(_LED_2_2, _tmpbuf2);
  }
}
