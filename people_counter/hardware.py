import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

# ----- LCD PINS -----
RS = 2
EN = 3
D4 = 4
D5 = 17
D6 = 27
D7 = 22

# ----- BUTTONS -----
ENTRY = 10
EXIT = 9

# ----- ALERT LED -----
ALERT_LED = 11

# ----- ADC PINS -----
ADC_D4 = 5
ADC_D5 = 6
ADC_D6 = 13
ADC_D7 = 19
ADC_WR = 26
ADC_RD = 21

lcd_pins = [RS, EN, D4, D5, D6, D7]
adc_data = [ADC_D4, ADC_D5, ADC_D6, ADC_D7]

for pin in lcd_pins:
    GPIO.setup(pin, GPIO.OUT)

for pin in adc_data:
    GPIO.setup(pin, GPIO.IN)

GPIO.setup(ENTRY, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(EXIT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ALERT_LED, GPIO.OUT)
GPIO.setup(ADC_WR, GPIO.OUT)
GPIO.setup(ADC_RD, GPIO.OUT)

# ----- LCD FUNCTIONS -----
def lcd_pulse():
    GPIO.output(EN, True)
    time.sleep(0.001)
    GPIO.output(EN, False)

def lcd_send(data, mode):
    GPIO.output(RS, mode)
    
    GPIO.output(D4, (data >> 4) & 1)
    GPIO.output(D5, (data >> 5) & 1)
    GPIO.output(D6, (data >> 6) & 1)
    GPIO.output(D7, (data >> 7) & 1)
    lcd_pulse()
    
    GPIO.output(D4, data & 1)
    GPIO.output(D5, (data >> 1) & 1)
    GPIO.output(D6, (data >> 2) & 1)
    GPIO.output(D7, (data >> 3) & 1)
    lcd_pulse()

def lcd_cmd(cmd):
    lcd_send(cmd, False)

def lcd_data(data):
    lcd_send(data, True)

def lcd_string(msg):
    for ch in msg:
        lcd_data(ord(ch))

# ----- ADC READ (4-bit only) -----
def read_adc():
    GPIO.output(ADC_WR, 0)
    time.sleep(0.001)
    GPIO.output(ADC_WR, 1)
    
    GPIO.output(ADC_RD, 0)
    value = 0
    
    for i in range(4):
        value |= (GPIO.input(adc_data[i]) << i)
    
    GPIO.output(ADC_RD, 1)
    return value * 2

# ----- MAIN -----
queue = 0
distributed = 0

lcd_cmd(0x28)
lcd_cmd(0x0C)
lcd_cmd(0x01)

while True:
    current_total = read_adc()
    display_weight = current_total - distributed
    required_weight = queue * 2
    
    if required_weight > display_weight and queue > 0:
        GPIO.output(ALERT_LED, 1)
    else:
        GPIO.output(ALERT_LED, 0)
    
    if GPIO.input(ENTRY) == 0:
        queue += 1
        time.sleep(0.3)
        
    if GPIO.input(EXIT) == 0:
        if queue > 0:
            queue -= 1
            distributed += 2
        time.sleep(0.3)
    
    lcd_cmd(0x01)
    lcd_cmd(0x80)
    lcd_string("Queue: " + str(queue))
    
    lcd_cmd(0xC0)
    lcd_string("Stock: " + str(display_weight))
    
    time.sleep(0.5)