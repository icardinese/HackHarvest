from flask import Flask, request, jsonify, redirect, url_for
from flask import render_template
import requests
import googlemaps
from scraperapi_sdk import ScraperAPIClient
from bs4 import BeautifulSoup
import openai
from flask_cors import CORS
from openai import OpenAI
import os

openai.api_key = "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"

client = OpenAI()

completion = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {
            "role": "user",
            "content": "Write a haiku about recursion in programming."
        }
    ]
)

print(completion.choices[0].message)

app = Flask(__name__)
CORS(app)

app.config['TEMPLATES_AUTO_RELOAD'] = True

spoonacularApiKey = "bfbc40cae6594c8ba8897bfc9abb1c27"
spoonacularEndpoint = "https://api.spoonacular.com/recipes/complexSearch"
import sqlite3

SCRAPERAPI_KEY = "4df84a5309ec81cc7dbaf3d1a1134fa3"
scraperapi_client = ScraperAPIClient(SCRAPERAPI_KEY)

recipes = []
from bs4 import BeautifulSoup
import requests

from googlemaps import Client as GoogleMapsClient

gmaps = GoogleMapsClient(key='AIzaSyCgYrzWtLZnfB4fpn8Z9l9zPdb66N2P2J8')

from bs4 import BeautifulSoup
import requests

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({"response": "No message provided"}), 400

        user_message = data['message']
        print(f"User message: {user_message}")

        # Use OpenAI's new SDK to get a response
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use "gpt-4" or "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are a helpful chatbot for food-related queries."},
                {"role": "user", "content": user_message}
            ]
        )

        bot_message = response['choices'][0]['message']['content']
        print(f"Bot response: {bot_message}")

        return jsonify({"response": bot_message})

    except Exception as e:
        print(f"Error in /chat endpoint: {e}")
        return jsonify({"response": "An error occurred while processing your request"}), 500
    

@app.route('/scrape_word', methods=['POST'])
def scrape_word():
    data = request.json
    url = data.get('url')
    keyword = data.get('keyword')

    if not url or not keyword:
        return jsonify({"error": "Missing URL or keyword"}), 400

    try:
        # Use ScraperAPI to fetch the page content
        response = scraperapi_client.get(url, params={"render": "true"})
        response = scraperapi_client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()  # Raise an error for HTTP issues

        # Parse the page content
        soup = BeautifulSoup(response.text, 'html.parser')

        # Search for the keyword in the page content
        if keyword.lower() in soup.get_text().lower():
            snippet_start = soup.get_text().lower().find(keyword.lower())
            snippet_end = snippet_start + 100
            snippet = soup.get_text()[snippet_start:snippet_end]
            return jsonify({"keyword_found": True, "snippet": snippet}), 200
        else:
            return jsonify({"keyword_found": False}), 200

    except Exception as e:
        print(f"Error during scraping: {e}")
        return jsonify({"error": "Failed to scrape the URL"}), 500

def get_snippet(text, keyword, context=30):
    """
    Extracts a snippet around the keyword with `context` characters before and after.
    """
    index = text.find(keyword.lower())
    if index == -1:
        return None
    start = max(index - context, 0)
    end = min(index + len(keyword) + context, len(text))
    return text[start:end]




def init_db():
    conn = sqlite3.connect('foodbanks.db')
    c = conn.cursor()
    # Create the foodbanks table
    c.execute('''
        CREATE TABLE IF NOT EXISTS foodbanks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            address TEXT,
            latitude REAL,
            longitude REAL,
            recipes TEXT,
            is_open INTEGER
        )
    ''')
    conn.commit()
    conn.close()

init_db()


@app.route('/', methods = ['GET', 'POST'])
def home():
    if request.method == "POST":
        print("POST method triggered")

        # Retrieve form data
        cuisine = request.form.get("origin")
        maxCalories = request.form.get("calories")
        sort = request.form.get("sortType")
        ingredients = request.form.get("ingredients")
        
        # Debugging form inputs
        print(f"Received Form Data - Cuisine: {cuisine}, MaxCalories: {maxCalories}, Sort: {sort}, Ingredients: {ingredients}")

        # Validation
        if not cuisine or not maxCalories or not sort or not ingredients:
            print("Validation failed: Missing fields")
            return render_template('index.html', error="Please fill out all fields")

        # API Call
        query_params = {
            "apiKey": spoonacularApiKey,
            "cuisine": cuisine,
            "maxCalories": maxCalories,
            "sort": sort,
            "includeIngredients": ingredients,
            "addRecipeInformation": "True",
            "addRecipeInstructions": "True",
            "addRecipeNutrition": "True"
        }
        try:
            response = requests.get(spoonacularEndpoint, params=query_params)
            response.raise_for_status()
            global recipes
            recipes = response.json().get("results", [])

            for recipe in recipes:
                # Create a new dictionary section in the original data for a parsed and more accesible nutrient information list
                info = {}
                # Access the 'nutrients' key inside 'nutrition'
                nutrients = recipe.get("nutrition", {}).get("nutrients", [])
                for nutrient in nutrients:
                    name = nutrient.get("name")
                    if name:  # Ensure 'name' exists
                        info[name] = {
                            "amount": nutrient.get("amount"),
                            "unit": nutrient.get("unit"),
                            "percentOfDailyNeeds": nutrient.get("percentOfDailyNeeds")
                        }
                recipe['nutrientinfo'] = info
        except Exception as e:
            print(f"Error during API call: {e}")
            return render_template('index.html', error="An error occurred while fetching recipes")
        return results()
    return render_template('index.html')

@app.route('/results', methods = ['GET', 'POST'])
def results():
    global recipes
    return render_template('results.html', recipes=recipes)

@app.route('/recipe/<int:recipe_id>')
def recipe_details(recipe_id):
    global recipes
    print(f"Received recipe_id: {recipe_id}")  # Debugging
    recipe = next((r for r in recipes if r["id"] == recipe_id), None)
    if not recipe:
        return "Recipe not found", 404
    return render_template('recipe.html', recipe=recipe)

@app.route('/foodbankfinder')
def foodbankfinder():
    print("Map Loaded")
    return render_template('foodbankfinder.html', map=map)

@app.route('/foodbank_requests', methods=['GET', 'POST'])
def foodbank_requests():
    if request.method == 'POST':
        # Handle form submission
        foodbank_name = request.form.get('foodbank_name')
        address = request.form.get('address')
        requested_recipes = request.form.get('requested_recipes')  # Comma-separated recipes

        # Save the request data to the database
        conn = sqlite3.connect('foodbanks.db')
        c = conn.cursor()

        # Check if the food bank already exists
        c.execute('SELECT id FROM foodbanks WHERE name = ? AND address = ?', (foodbank_name, address))
        existing = c.fetchone()

        if existing:
            # Update recipes for the existing food bank
            c.execute('UPDATE foodbanks SET recipes = ? WHERE id = ?', (requested_recipes, existing[0]))
        else:
            # Insert a new entry if it doesn't exist
            c.execute(
                'INSERT INTO foodbanks (name, address, recipes) VALUES (?, ?, ?)',
                (foodbank_name, address, requested_recipes)
            )

        conn.commit()
        conn.close()

        return render_template('request_success.html', foodbank_name=foodbank_name)

    # Handle pre-filled data for GET request
    foodbank_name = request.args.get('name', '')
    address = request.args.get('address', '')

    return render_template(
        'foodbank_form.html',
        foodbank_name=foodbank_name,
        address=address
    )

@app.route('/redirect_to_form/<name>/<address>')
def redirect_to_form(name, address):
    # Redirect to the form with pre-filled data
    return redirect(url_for('foodbank_requests', name=name, address=address))



@app.route('/update_recipes', methods=['POST'])
def update_recipes():
    data = request.json
    name = data['name']
    address = data['address']
    recipes = data.get('recipes', '')

    conn = sqlite3.connect('foodbanks.db')
    c = conn.cursor()

    # Check if the food bank already exists
    c.execute('SELECT id FROM foodbanks WHERE name = ? AND address = ?', (name, address))
    existing = c.fetchone()

    if existing:
        # Update recipes for the existing food bank
        c.execute('UPDATE foodbanks SET recipes = ? WHERE id = ?', (recipes, existing[0]))
    else:
        # Insert a new entry if it doesn't exist
        c.execute(
            'INSERT INTO foodbanks (name, address, recipes) VALUES (?, ?, ?)',
            (name, address, recipes)
        )

    conn.commit()
    conn.close()

    return jsonify({"message": "Recipes updated successfully!"})


@app.route('/submit_foodbank', methods=['POST'])
def submit_foodbank():
    name = request.form['name']
    address = request.form['address']
    recipes = request.form.get('recipes', '')

    # Geocode the address to get latitude and longitude
    try:
        geocode_result = gmaps.geocode(address)
        latitude = geocode_result[0]['geometry']['location']['lat']
        longitude = geocode_result[0]['geometry']['location']['lng']
    except Exception as e:
        print(f"Error geocoding address '{address}': {e}")
        latitude, longitude = None, None

    conn = sqlite3.connect('foodbanks.db')
    c = conn.cursor()

    # Insert the new food bank into the database
    c.execute(
        'INSERT INTO foodbanks (name, address, recipes, latitude, longitude) VALUES (?, ?, ?, ?, ?)',
        (name, address, recipes, latitude, longitude)
    )

    conn.commit()
    conn.close()

    return render_template('request_success.html', foodbank_name=name)


@app.route('/get_foodbanks', methods=['GET'])
def get_foodbanks():
    conn = sqlite3.connect('foodbanks.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM foodbanks")
    rows = c.fetchall()

    foodbanks = []
    for row in rows:
        latitude = row["latitude"]
        longitude = row["longitude"]
        address = row["address"]

        # If latitude or longitude is missing, geocode the address
        if latitude is None or longitude is None:
            try:
                geocode_result = gmaps.geocode(address)
                if geocode_result:
                    latitude = geocode_result[0]["geometry"]["location"]["lat"]
                    longitude = geocode_result[0]["geometry"]["location"]["lng"]

                    # Update the database with the fetched coordinates
                    c.execute(
                        "UPDATE foodbanks SET latitude = ?, longitude = ? WHERE id = ?",
                        (latitude, longitude, row["id"]),
                    )
                    conn.commit()
            except Exception as e:
                print(f"Error geocoding address '{address}': {e}")
                latitude, longitude = None, None

        foodbanks.append({
            "name": row["name"],
            "address": row["address"],
            "latitude": latitude,
            "longitude": longitude,
            "recipes": row["recipes"].split(',') if row["recipes"] else [],
            "is_open": bool(row["is_open"]),
        })

    conn.close()
    return jsonify(foodbanks)

def find_nearby_foodbanks(latitude, longitude, radius):
    import sqlite3
    from math import radians, sin, cos, sqrt, atan2

    # Convert degrees to radians for calculation
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371e3  # Earth radius in meters
        φ1 = radians(lat1)
        φ2 = radians(lat2)
        Δφ = radians(lat2 - lat1)
        Δλ = radians(lon2 - lon1)

        a = sin(Δφ / 2) ** 2 + cos(φ1) * cos(φ2) * sin(Δλ / 2) ** 2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return R * c

    # Connect to your SQLite database
    conn = sqlite3.connect('foodbanks.db')
    c = conn.cursor()

    # Fetch all foodbanks and calculate distances
    c.execute("SELECT name, address, latitude, longitude, recipes, is_open FROM foodbanks")
    foodbanks = c.fetchall()
    matching_foodbanks = []
    for foodbank in foodbanks:
        recipes_list = foodbank['recipes'].split(",") if foodbank['recipes'] else []

        # Check if the query matches any recipe
        if food_item in [r.strip().lower() for r in recipes_list]:
            matching_foodbanks.append({
                "name": foodbank['name'],
                "address": foodbank['address'],
                "recipes": recipes_list,
                "latitude": foodbank['latitude'],
                "longitude": foodbank['longitude'],
                "is_open": foodbank['is_open'],
            })


    return nearby_foodbanks


@app.route('/search_food', methods=['POST'])
def search_food():
    data = request.json
    food_item = data.get('food_item', '').lower()
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    radius = data.get('radius', 10000)

    conn = sqlite3.connect('foodbanks.db')
    c = conn.cursor()

    # Select foodbanks within the radius
    c.execute('SELECT * FROM foodbanks')
    foodbanks = c.fetchall()

    matching_foodbanks = []
    for foodbank in foodbanks:
        foodbank_name, address, recipes, lat, lng, is_open = foodbank
        recipes_list = recipes.split(",") if recipes else []

        # Check if the query matches any recipe
        if food_item in [r.strip().lower() for r in recipes_list]:
            matching_foodbanks.append({
                "name": foodbank_name,
                "address": address,
                "recipes": recipes_list,
                "latitude": lat,
                "longitude": lng,
                "is_open": is_open,
            })

    conn.close()
    print(matching_foodbanks)

    return jsonify({"matching_foodbanks": matching_foodbanks})




def scrap_foodbank_website(url, food_item):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Search for the food item in the page context
    if food_item.lower() in soup.get_text().lower():
        return True
    return False

if __name__ == "__main__":
    app.run(debug=True)
