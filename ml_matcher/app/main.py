from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/analyze', methods=['POST'])
def analyze_resume():
    """Simple test endpoint"""
    return jsonify({
        "message": "ML service is working",
        "match_score": 85.5,
        "skills_identified": ["Python", "JavaScript", "React"],
        "missing_skills": [("AWS", 90), ("Docker", 85)],
        "recommendations": ["Sample recommendation"]
    })

# Make sure this is present for direct execution
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)