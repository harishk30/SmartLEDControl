import openai
import json
import logging
import board
import neopixel
import time
import keyboard

logging.basicConfig(level=logging.INFO)



LED_PIN = board.D18  
NUM_LEDS = 300  
ORDER = neopixel.GRB  

pixels = neopixel.NeoPixel(LED_PIN, NUM_LEDS, brightness=0.5, auto_write=False, pixel_order=ORDER)

def get_gpt_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use GPT-4 model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates JSON commands to control LED lights. Ensure that all your responses are formatted as valid JSON. The JSON should contain a 'pattern' key with an array of objects, each containing 'r', 'g', 'b', and 'duration' keys. Each duration should be at least 3000 ms. Ensure that the colors are accurate and use RGB values."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message['content'].strip() 
    except Exception as e:
        logging.error(f"Error getting GPT response: {e}")
        return "Error getting GPT response."
    
def gamma_correction(r, g, b):
    r = int((r/255.0) ** 1.9 * 255.0)
    g = int((g/255.0) ** 1.9 * 255.0)
    b = int((b/255.0) ** 1.9 * 255.0)
    return (r, g, b)

def gamma_decode(r, g, b):
    r = int((r/255.0) ** (1/1.9) * 255.0)
    g = int((g/255.0) ** (1/1.9) * 255.0)
    b = int((b/255.0) ** (1/1.9) * 255.0)
    return (r, g, b)

def control_led(command):
    try:
        led_command = json.loads(command)
        if "pattern" in led_command:
            apply_led_pattern(led_command["pattern"])
            return "LED pattern set."
        else:
            return "Invalid command format."
    except json.JSONDecodeError:
        logging.error("Invalid JSON command.")
        return "Invalid JSON command."
    
def fade_between_colors(color1, color2, duration, steps=300):
    step_duration = duration / steps
    for step in range(steps):
        if keyboard.is_pressed('space'):
            return  
        intermediate_color = (
            int(color1[0] + (color2[0] - color1[0]) * step / steps),
            int(color1[1] + (color2[1] - color1[1]) * step / steps),
            int(color1[2] + (color2[2] - color1[2]) * step / steps)
        )
        intermediate_color = gamma_correction(*intermediate_color)
        for i in range(NUM_LEDS):
            pixels[i] = intermediate_color
        pixels.show()
        time.sleep(step_duration / 1000)
    
def apply_led_pattern(pattern):
    try:
        while True:
            for i in range(len(pattern)):
                if keyboard.is_pressed('space'):
                    return  # Exit the function if space is pressed
                current_color = gamma_correction(pattern[i]["r"], pattern[i]["g"], pattern[i]["b"])
                next_color = gamma_correction(pattern[(i + 1) % len(pattern)]["r"], pattern[(i + 1) % len(pattern)]["g"], pattern[(i + 1) % len(pattern)]["b"])
                duration = pattern[i]["duration"]
                fade_between_colors(current_color, next_color, duration)
    except Exception as e:
        logging.error(f"Error applying LED pattern: {e}")

def main():
    user_input = input("Describe the LED pattern you want: ")
    gpt_response = get_gpt_response(user_input)
    print(f"GPT-4 Response: {gpt_response}")
    led_response = control_led(gpt_response)
    print(f"LED Response: {led_response}")

if __name__ == '__main__':
    main()
