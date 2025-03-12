#include <Wire.h>
#include <LiquidCrystal_I2C.h>

LiquidCrystal_I2C lcd(0x27, 16, 2);

void setup() {
  // Initialize the LCD
  lcd.init();
  lcd.backlight();
  Serial.begin(9600); // Initialize serial communication
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    
    if (line.startsWith("lcd 1 ")) {
      // Display song name on the first line
      lcd.setCursor(0, 0);  // Set cursor to the first row
      lcd.print(line.substring(6)); // Show the song name
    } 
    else if (line.startsWith("lcd 2 ")) {
      // Display progress bar and time on the second line
      lcd.setCursor(0, 1);  // Set cursor to the second row
      lcd.print(line.substring(6)); // Show progress bar and time
    }
  }
}
