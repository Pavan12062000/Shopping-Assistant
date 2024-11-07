from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import re
import random

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Define the cart as a global variable
cart = {}   # Initialize an empty dictionary to hold cart items (product_name: quantity)
order_status = ["Order Placed", "Order Confirmed", "Order Shipped", "Out for Delivery", "Delivered"] # Define order statuses
shopping_keywords = [
    "cart", "add to cart", "remove from cart", "product", "price", "availability", "specifications", 
    "details", "shipping", "delivery", "checkout", "payment", "order", "quantity", "stock", "items", 
    "order status", "recommend", "purchase", "in stock", "out of stock", "available", "how much", 
    "cost", "order status", "can I buy", "buy", "get", "when will my order", "how many pieces"
]  # Define keywords related to shopping

# Function to check if the query is shopping-related
def is_shopping_query(user_prompt):
    # Check if the user query contains any shopping-related keywords
    if any(keyword in user_prompt.lower() for keyword in shopping_keywords):
        return True
    
    # Handle more complex cases like availability or price
    if re.search(r"(available|stock|price|cost|buy|order|pieces|how much)", user_prompt, re.IGNORECASE):
        return True
    
    return False

def format_response_text(text):
    # Check if the "Add to cart" note already exists
    if "1. If you want to add any product into the cart" not in text:
        text += "<br><br>NOTE: <br> 1. If you want to add any product into the cart, please send 'Add to cart - product name'."
        text += "<br> 2. If you want to view your cart, please send 'View cart'."
        text += "<br> 3. If you want to remove any product from the cart, please send 'Remove from cart - product name'."
    # Replace **text** with <strong>text</strong> for bold formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Add line breaks for readability
    text = text.replace("\n\n", "<br><br>").replace("\n", "<br>")
    return text

def send_prompt_to_ollama(prompt):
    model_name = "llama3"  # Use the pulled model name

    # Run the Ollama CLI command without the '-p' flag, passing the prompt via stdin
    result = subprocess.run(
        ["ollama", "run", model_name],
        input=prompt,
        capture_output=True,
        text=True,
        encoding="utf-8"  # Ensure the output is correctly decoded
    )
    
    # Check if the command was successful and return the output
    if result.returncode == 0:
        response_text = result.stdout.strip()
        return format_response_text(response_text)  # Format text before returning
    else:
        print("Error:", result.stderr)
        return "An error occurred while processing the prompt."
    
def count_digits(input_value):
    length = 0
    length = len(input_value)
    if length == 10:
        return True
    else:    
        return False

@app.route("/ask", methods=["POST"])
def ask_ollama():
    global last_added_product  # Ensure we're using the global variable

    data = request.get_json()
    user_prompt = data.get("prompt")
    selected_product = data.get("selectedProduct")  # Retrieve selectedProduct from the request
    print("user prompt", user_prompt)

    # Ignore blank input
    if not user_prompt:
        return jsonify({"response": ""})  # Return an empty response to skip processing

    # Check if the query is shopping-related
    if is_shopping_query(user_prompt):
        #proceed with shopping-related queries
        # Check if prompt matches the "Add to cart - product name" pattern
        if user_prompt.startswith("Add to cart - "):
            print("Add to cart command detected")
            product_name = user_prompt.split("Add to cart - ", 1)[1].strip()  # Extract the product name
            # Check if product_name is empty
            if not product_name:
                ollama_response = "Please specify the product you want to add to your cart."
            else:
                # Check if product already exists in the cart
                product_name_lower = product_name.lower()
                last_added_product = product_name_lower  # Store the last added product
                if product_name_lower in cart:
                    # Ask user if they want to add another piece
                    ollama_response = f"{product_name.capitalize()} is already in your cart. Do you want to add another piece of {product_name.capitalize()}? (Yes/No)"
                else:
                    # Add the product to the cart
                    print("item added to cart")
                    cart[product_name_lower] = 1
                    ollama_response = f"{product_name.capitalize()} has been added to your cart!"

        # Handle user response to add another piece to the cart
        elif user_prompt.lower() in ["yes", "no"] and user_prompt.lower() == "yes" and last_added_product in cart:
            # Add another piece to the cart
            cart[last_added_product] += 1
            ollama_response = f"Another piece of {last_added_product.capitalize()} has been added to your cart."
        elif user_prompt.lower() == "no" and last_added_product in cart:
            ollama_response = f"{last_added_product.capitalize()} will not be added again to your cart."

        # Handle Remove from Cart command
        elif user_prompt.startswith("Remove from cart - "):
            product_name = user_prompt.split("Remove from cart - ", 1)[1].strip()  # Extract the product name
            # Check if product_name is empty
            if not product_name:
                ollama_response = "Please specify the product you want to remove from your cart."
            # Check if cart is empty
            elif not cart:
                ollama_response = "Your cart is empty! There's nothing to remove."
            # Handle case insensitivity for product name comparison
            elif any(product.lower() == product_name.lower() for product in cart):
                product_name_lower = product_name.lower()
                # If quantity is more than 1, reduce the quantity
                if cart[product_name_lower] > 1:
                    cart[product_name_lower] -= 1
                    ollama_response = f"One piece of {product_name.capitalize()} has been removed from your cart. {cart[product_name_lower]} piece(s) left."
                # If only 1 item left, remove the item from the cart
                else:
                    del cart[product_name_lower]
                    ollama_response = f"{product_name.capitalize()} has been removed from your cart."
            else:
                ollama_response = f"{product_name.capitalize()} is not in your cart."

        # Handle user prompts according to their context
        elif user_prompt == "Find products":
            ollama_response = "Sure! Please tell me the type of products you’re looking for."

        elif user_prompt == "Product-related queries":
            ollama_response = "What product do you have queries about?"
        elif user_prompt.startswith("Product: "):  # Detect questions about specific products
            product_question = user_prompt.split(": ", 1)[1]  # Extract the question
            if any(keyword in product_question.lower() for keyword in ["specifications", "details", "features"]):
                ollama_response = send_prompt_to_ollama(f"Can you provide the specifications for {selected_product}?")
            elif any(keyword in product_question.lower() for keyword in ["price", "cost", "how much"]):
                ollama_response = send_prompt_to_ollama(f"What is the price of {selected_product}?")
            elif any(keyword in product_question.lower() for keyword in ["availability", "in stock", "available"]):
                n = random.randint()
                if(n<10):
                    ollama_response = f"Yes, the {selected_product} is currently available! However, we only have {n} piece(s) left in stock, so you may want to act quickly if you're interested. Would you like to add it to your cart?"
                elif (n>10):
                    ollama_response = f"Yes, the {selected_product} is currently available! We have more than 10 pieces in stock. Would you like to add it to your cart?"
                elif (n==0):
                    ollama_response = f"Sorry, the {selected_product} is currently out of stock. Would you like to be notified when it's back in stock?"
            else:
                # Default response for unspecified questions
                ollama_response = send_prompt_to_ollama(f"Answer the following question about {selected_product}: {product_question}")
        elif user_prompt == "Recommendations":
            ollama_response = "I'd be happy to recommend some products! What category interests you?"

        elif "checkout" in user_prompt.lower():
            ollama_response = "To proceed to checkout, please review your cart, enter your shipping information, and choose your payment method."

        elif "payment" in user_prompt.lower() or "pay" in user_prompt.lower():
                ollama_response = "We accept payments via credit/debit cards, PayPal, and other secure methods."

        # Handle delivery time queries
        elif "delivery time" in user_prompt.lower() or "when will my order arrive" in user_prompt.lower():
                ollama_response = "Delivery times usually range from 3 to 5 business days depending on your location and selected shipping method."
        else:
            # Default behavior: send the prompt to Ollama for processing
            ollama_response = send_prompt_to_ollama(user_prompt)

        formatted_response = format_response_text(ollama_response)  # Ensure response is formatted
        print("Ollama response:", formatted_response)
    return jsonify({"response": formatted_response})

@app.route("/view_cart", methods=["GET"])
def view_cart():
    if cart:
        # Format items with their quantities
        items = "<br>".join([f"{product.capitalize()} - {quantity} piece(s)" for product, quantity in cart.items()])
        response = f"Your cart contains:<br>{items}"
    else:
        response = "Your cart is empty."
    formatted_response = format_response_text(response)  # Ensure response is formatted
    print("Ollama response:", formatted_response)
    return jsonify({"response": formatted_response})

@app.route("/track_order", methods = ["POST"])
def track_order():
    if request.method == "POST":
        data = request.get_json()
        tracking_id = data.get("prompt")
        trackingId = str(tracking_id)
        if(trackingId.isnumeric()):
            if count_digits(trackingId):
                n = random.randint(0,5)
                ollama_response = f"Here is the latest update for your order (ID: {trackingId}): <b>{order_status[n]}</b>. If you have more questions, feel free to ask!"
            else:
                ollama_response = "Please provide a valid tracking ID."
        else:
            ollama_response = "Please provide a valid tracking ID."
    formatted_response = format_response_text(ollama_response)  # Ensure response is formatted
    print("Ollama response:", formatted_response)
    return jsonify({"response": formatted_response})

if __name__ == "__main__":
    app.run(debug=True)
