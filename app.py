from flask import Flask, request, jsonify, redirect, url_for
from flask import render_template
import requests
import googlemaps
from bs4 import BeautifulSoup

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

spoonacularApiKey = "bfbc40cae6594c8ba8897bfc9abb1c27"
spoonacularEndpoint = "https://api.spoonacular.com/recipes/complexSearch"
import sqlite3

recipes = []

from bs4 import BeautifulSoup
import requests

def scrape_foodbank_website(url, search_terms):
    try:
        # Send a GET request to the website
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parse the website HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Search for the terms in the website's text content
        website_text = soup.get_text().lower()
        for term in search_terms:
            if term.lower() in website_text:
                return True  # Found the term
        return False  # None of the terms matched
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return False


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

    # Optional: Geocode the address to get latitude and longitude
    geocoder = googlemaps.Client(key='AIzaSyCgYrzWtLZnfB4fpn8Z9l9zPdb66N2P2J8')
    geocode_result = geocoder.geocode(address)
    latitude = geocode_result[0]['geometry']['location']['lat']
    longitude = geocode_result[0]['geometry']['location']['lng']

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

    foodbanks = [
        {
            "name": row["name"],
            "address": row["address"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "recipes": row["recipes"].split(',') if row["recipes"] else [],
            "is_open": bool(row["is_open"]),
        }
        for row in rows
    ]
    print(foodbanks)

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
