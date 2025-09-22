#include <Arduino.h>

// put function declarations here:
int myFunction(int, int);

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  int result = myFunction(2, 3);
}

void loop() {
  // put your main code here, to run repeatedly:
  delay(100);
  for (int i = 0; i < 20; i++){
    Serial.print("Number is : ");
    Serial.println(i);
    delay(100);
  }
}

// put function definitions here:
int myFunction(int x, int y) {
  return x + y;
}