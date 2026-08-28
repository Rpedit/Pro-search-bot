from flask import Flask
app = Flask(__name__)

@app.route('/')
def home():
    return "Auto-Filter Bot with Dual DB & Pagination is running 24/7!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
