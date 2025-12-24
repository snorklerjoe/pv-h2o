/* 
  Control.h - Library for controlling our homemade solar DC ground fault system.
  Written by Joseph R. Freeston, hardware by Andrew K. Freeston, 2020.
*/

#ifndef Ctrl_h
#define Ctrl_h

#include "Arduino.h"

#define STAT_OK        0x00  // Okay, normal status (No ground fault)
#define STAT_TRIPPED   0x01  // Eh, it tripped because of a fault
#define STAT_FAULT     0x02  // Uh oh, it tried to trip but the ground fault remains

#define CIRC_NUM1      0x01  //Circuit 1
#define CIRC_NUM2      0x02  //Circuit 2

#define ANALOGSAMPLES  10

typedef unsigned char Status;

class Panel {
  public:
    void init();                                // Initialize the library
    void set_status(int circuit, Status stat);  // Set the status (displayed w/ the LEDs on the front of the panel)
    Status get_status(int circuit);             // Get the status
    double get_current(int sensor);                // Get the current from a sensor, sensors are 1, 2, 3, and 4.
    void turn_on(int circuit);                  // For turning on a circuit
    void turn_off(int circuit);                 // For turning off a circuit
    void loop();                                // This should be run over and over again.
  private:
    // Pin Declarations:
    const unsigned char _LED_1_1 = 10;
    const unsigned char _LED_1_2 = 11;
    const unsigned char _LED_2_1 = 12;
    const unsigned char _LED_2_2 = 13;

    // Status:
    Status _status1 = STAT_TRIPPED;  // Circuit 1
    Status _status2 = STAT_TRIPPED;  // Circuit 2

    void _alert(String text);        // Alert the user via the serial terminal. NOTE: This pauses for 500 ms, and should only be called after time-sensitive threats are gone.
    void _note(String text);         // Display a brief note on the serial terminal.

    void _blinky();                  // An aesthetically pleasing display for initialization

    bool _tmpbuf1, _tmpbuf2;         // Temporary buffers for blinking in FAULT STATUS mode.
};

#endif
