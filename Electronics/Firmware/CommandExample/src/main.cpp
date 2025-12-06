#include <Arduino.h>
#include <CmdMessenger.h>
#include "dataModel.h"
#include "df4MotorDriver.h"
#include <Wire.h>
#include <SparkFun_AS7343.h>

SfeAS7343ArdI2C mySensor;
//int initialRed;
//int initialBlue;
//int initialGreen;

// Initialize CmdMessenger: Serial, field sep ',', cmd sep ';', escape '/'
CmdMessenger cmdMessenger(Serial, ',', ';', '/');

// Forward declarations
void OnUnknownCommand();
void OnWatchdogRequest();
void OnArduinoReady();
void OnReceiveStart();   // pump A
void OnReceiveStartB();  // pump B
void OnReceiveStartC();  // pump C
void OnReceiveStop();

void receiveStart();     // pump A
void receiveStartB();    // pump B
void receiveStartC();    // pump C
void receiveStop();

void OnReceiveReadColor();
void receiveReadColor();

// Command IDs – MUST match Python 'commands' list order
enum
{
  kWatchdog,    // 0
  kAcknowledge, // 1
  kError,       // 2
  kStart,       // 3  pump A
  kStartB,      // 4  pump B
  kStartC,      // 5  pump C
  kStop,        // 6  stop all pumps
  kReadColor,   // 7  record current color
};

// Attach callbacks
void attachCommandCallbacks()
{
  // Default handler
  cmdMessenger.attach(OnUnknownCommand);

  // Commands
  cmdMessenger.attach(kWatchdog, OnWatchdogRequest);
  cmdMessenger.attach(kStart,    OnReceiveStart);   // pump A
  cmdMessenger.attach(kStartB,   OnReceiveStartB);  // pump B
  cmdMessenger.attach(kStartC,   OnReceiveStartC);  // pump C
  cmdMessenger.attach(kStop,     OnReceiveStop);
  cmdMessenger.attach(kReadColor,  OnReceiveReadColor);
}

// ------------------  C A L L B A C K S -----------------------

// Called when a received command has no attached function
void OnUnknownCommand()
{
  cmdMessenger.sendCmd(kError, "Command without attached callback");
}

void OnWatchdogRequest()
{
  // Respond with device ID
  cmdMessenger.sendCmd(kWatchdog, "0000000-0000-0000-0000-00000000001");
}

// Optional: can be used if you want a separate "ready" message
void OnArduinoReady()
{
  cmdMessenger.sendCmd(kAcknowledge, "Arduino ready");
}

void OnReceiveStart()
{
  receiveStart();
}

void OnReceiveStartB()
{
  receiveStartB();
}

void OnReceiveStartC()
{
  receiveStartC();
}

void OnReceiveStop()
{
  receiveStop();
}

void OnReceiveReadColor()
{
  receiveReadColor();
}

// ------------------  S E T U P  /  L O O P  ------------------

void setup()
{
  Serial.begin(115200);
  setupPumps();

  // Do not print CR/LF at end of command to save bytes
  cmdMessenger.printLfCr(false);

  // read color code here
  Wire.begin();

  if (mySensor.begin() == false)
  {
    Serial.println("AS7343: Sensor failed to begin. Check wiring!");
    while (1) ; // halt
  }
  Serial.println("AS7343: Sensor began.");

  if (mySensor.powerOn() == false)
  {
    Serial.println("AS7343: Failed to power on device.");
    while (1) ;
  }
  Serial.println("AS7343: Device powered on.");

  if (mySensor.setAutoSmux(AUTOSMUX_18_CHANNELS) == false)
  {
    Serial.println("AS7343: Failed to set AutoSmux.");
    while (1) ;
  }
  Serial.println("AS7343: AutoSmux set to 18 channels.");

  if (mySensor.enableSpectralMeasurement() == false)
  {
    Serial.println("AS7343: Failed to enable spectral measurement.");
    while (1) ;
  }
  Serial.println("AS7343: Spectral measurement enabled.");

  // read color code ends here

  // Attach callbacks
  attachCommandCallbacks();

  // Initial message for Python to read on startup
  cmdMessenger.sendCmd(kAcknowledge, "Arduino has started!");
}

void loop()
{
  // Process incoming serial data
  cmdMessenger.feedinSerialData();
}

// ------------------  R E C E I V E R S  ----------------------

void receiveStart()
{
  // Pump A: matches "?I?"  -> bool, unsigned int, bool
  bool state = cmdMessenger.readBinArg<bool>();
  unsigned int speed = cmdMessenger.readBinArg<unsigned int>();
  bool dir = cmdMessenger.readBinArg<bool>();

  pumpA.state = state;
  pumpA.speed = speed;
  pumpA.dir   = dir;

  if (pumpA.state)
  {
    StartPumpA(pumpA.speed, pumpA.dir);
  }
  else
  {
    StopPumpA();
  }

  // Acknowledge so Python receive() returns
  cmdMessenger.sendCmd(kAcknowledge, "StepA");
}

void receiveStartB()
{
  // Pump B: matches "?I?"
  bool state = cmdMessenger.readBinArg<bool>();
  unsigned int speed = cmdMessenger.readBinArg<unsigned int>();
  bool dir = cmdMessenger.readBinArg<bool>();

  pumpB.state = state;
  pumpB.speed = speed;
  pumpB.dir   = dir;

  if (pumpB.state)
  {
    StartPumpB(pumpB.speed, pumpB.dir);
  }
  else
  {
    StopPumpB();
  }

  cmdMessenger.sendCmd(kAcknowledge, "StepB");
}

void receiveStartC()
{
  // Pump C: matches "?I?"
  bool state = cmdMessenger.readBinArg<bool>();
  unsigned int speed = cmdMessenger.readBinArg<unsigned int>();
  bool dir = cmdMessenger.readBinArg<bool>();

  pumpC.state = state;
  pumpC.speed = speed;
  pumpC.dir   = dir;

  if (pumpC.state)
  {
    StartPumpC(pumpC.speed, pumpC.dir);
  }
  else
  {
    StopPumpC();
  }

  cmdMessenger.sendCmd(kAcknowledge, "StepC");
}

void receiveStop()
{
  // Stop all pumps (implemented in df4MotorDriver/dataModel)
  stopPumps();

  // Let Python know we’re done
  cmdMessenger.sendCmd(kAcknowledge, "Stopped");
}

void receiveReadColor()
{
  // Turn on onboard white LED at minimal drive (optional)
  mySensor.setLedDrive(0); // 0 = 4mA
  mySensor.ledOn();
  delay(500); // let light stabilize a bit

  if (mySensor.readSpectraDataFromSensor() == false)
  {
    mySensor.ledOff();
    cmdMessenger.sendCmd(kError, "Failed to read spectral data");
    return;
  }

  mySensor.ledOff();

  // Use SparkFun API to get Blue / Red / Green etc. 
  uint16_t red   = mySensor.getRed();
  uint16_t green = mySensor.getGreen();
  uint16_t blue  = mySensor.getBlue();

  // Send R,G,B back to the PC as three binary uint16_t
  cmdMessenger.sendCmdStart(kReadColor);
  cmdMessenger.sendCmdBinArg(red);
  cmdMessenger.sendCmdBinArg(green);
  cmdMessenger.sendCmdBinArg(blue);
  cmdMessenger.sendCmdEnd();
}
