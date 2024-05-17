import openai
import json
import logging
import board
import neopixel
import time

logging.basicConfig(level=logging.INFO)



LED_PIN = board.D18  
NUM_LEDS = 300  
ORDER = neopixel.GRB  

pixels = neopixel.NeoPixel(LED_PIN, NUM_LEDS, brightness=0.5, auto_write=False, pixel_order=ORDER)

def get_gpt_response(prompt):
    try:
        response = openai.Completion.create(
            model="gpt-4",  # Use GPT-4 model
            messages=[
                {"role": "system", "content": "You are a helpful assistant that generates JSON commands to control LED lights."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        logging.error(f"Error getting GPT response: {e}")
        return "Error getting GPT response."

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
    
def apply_led_pattern(pattern):
    try:
        for step in pattern:
            color = (step["r"], step["g"], step["b"])
            duration = step["duration"]
            for i in range(NUM_LEDS):
                pixels[i] = color
            pixels.show()
            time.sleep(duration / 1000)
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
