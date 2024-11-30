from flask import Flask, request, jsonify
from flask import render_template
import requests

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

spoonacularApiKey = "bfbc40cae6594c8ba8897bfc9abb1c27"
spoonacularEndpoint = "https://api.spoonacular.com/recipes/complexSearch"

recipes = []

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
        # Collect data from the form
        foodbank_name = request.form.get('foodbank_name')
        address = request.form.get('address')
        requested_recipes = request.form.get('requested_recipes')  # Comma-separated recipes

        # Save the request data (you can replace this with database logic)
        # For now, save it in a global list or JSON file
        with open('foodbank_requests.json', 'a') as f:
            f.write(f"{foodbank_name},{address},{requested_recipes}\n")

        return render_template('request_success.html', foodbank_name=foodbank_name)

    return render_template('foodbank_form.html')

@app.route('/get_requests')
def get_requests():
    with open('foodbank_requests.json', 'r') as f:
        requests = f.readlines()
    return jsonify([line.strip().split(',') for line in requests])


if __name__ == "__main__":
    app.run(debug=True)
