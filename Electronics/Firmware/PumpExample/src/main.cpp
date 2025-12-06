#include <Arduino.h>
#include "dataModel.h"
#include "df4MotorDriver.h"
#include <SparkFun_AS7343.h>

SfeAS7343ArdI2C mySensor;
int c = 0;

void setup() {
  Serial.begin(115200);
  delay(3000);
  Serial.println("Setup started");
  setupPumps();
  Serial.println("Setup finished");
}

void loop() {
while (c < 45) {
  // delay(300);
  //Serial.println("Starting pump A forward at full speed for 3 seconds");
  // StartPumpB(4096, HIGH);

  // delay(300);
  // Serial.println("Starting pump B forward at half speed for 3 seconds");
  // StartPumpA(4096, HIGH);

  delay(300);
  // Serial.println("Starting pump C forward at half speed for 3 seconds");
  StartPumpC(4096, HIGH);

  c += 1;
  delay(300);
  stopPumps();
  // Serial.println("Pumps stopped");
}

}



