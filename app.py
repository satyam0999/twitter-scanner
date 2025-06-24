from flask import Flask, render_template, request, jsonify
import json
import time
import os
import uuid
from datetime import datetime

# Try to import optional dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    print("⚠️ OpenAI not available - using mock analysis")
    OPENAI_AVAILABLE = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️ python-dotenv not available - using os.environ directly")

app = Flask(__name__)

# In-memory storage for analysis results
analysis_cache = {}

# Cache for user lookups to avoid repeated API calls
user_cache = {}

# Global Twitter client to avoid repeated logins
twitter_client = None
client_logged_in = False

# Configuration - Use environment variables
USERNAME = os.environ.get('USERNAME', 'demo_user')
EMAIL = os.environ.get('EMAIL', 'demo@example.com') 
PASSWORD = os.environ.get('PASSWORD', 'demo_password')
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# Debug environment variables
print("🔧 Environment Variables:")
print(f"   USERNAME: {USERNAME}")
print(f"   EMAIL: {EMAIL}")
print(f"   PASSWORD: {'*' * len(PASSWORD) if PASSWORD else 'Not set'}")
print(f"   OPENAI_API_KEY: {'✅ Set' if OPENAI_API_KEY else '❌ Missing'}")
print(f"   OPENAI_AVAILABLE: {OPENAI_AVAILABLE}")

class TweetAnalyzer:
    def __init__(self, openai_api_key):
        self.openai_available = OPENAI_AVAILABLE and openai_api_key
        if self.openai_available:
            try:
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                print("✅ OpenAI client initialized")
            except Exception as e:
                print(f"❌ OpenAI client initialization failed: {e}")
                self.openai_available = False
    
    def analyze_tweet(self, tweet_text):
        """
        Analyze a single tweet for hateful, violent, or anti-America content
        """
        if not self.openai_available:
            # Return mock analysis when OpenAI is not available
            return self._mock_analysis(tweet_text)
        
        prompt = f"""
        Analyze this tweet and determine if it contains any of the following:
        1. Hateful content (discrimination, harassment, hate speech)
        2. Violent content (threats, incitement to violence, graphic violence)
        3. Anti-America content (criticism of US policies, institutions, or people)

        Tweet: "{tweet_text}"

        You MUST respond with ONLY valid JSON in this exact format (no additional text):
        {{
            "hateful": true,
            "violent": false,
            "anti_america": false,
            "confidence": "high",
            "explanation": "Brief explanation here",
            "severity": "low"
        }}

        Use only: true/false for booleans, "high"/"medium"/"low" for confidence, "none"/"low"/"medium"/"high" for severity.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a content moderator. Respond ONLY with valid JSON, no other text."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.0
            )
            
            response_text = response.choices[0].message.content.strip()
            
            # Clean the response
            if response_text.startswith('```json'):
                response_text = response_text.replace('```json', '').replace('```', '').strip()
            elif response_text.startswith('```'):
                response_text = response_text.replace('```', '').strip()
            
            # Find JSON content
            start = response_text.find('{')
            end = response_text.rfind('}') + 1
            if start != -1 and end != 0:
                json_text = response_text[start:end]
            else:
                json_text = response_text
            
            result = json.loads(json_text)
            
            # Validate required fields
            required_fields = ['hateful', 'violent', 'anti_america', 'confidence', 'explanation', 'severity']
            for field in required_fields:
                if field not in result:
                    result[field] = False if field in ['hateful', 'violent', 'anti_america'] else 'unknown'
            
            return result
            
        except Exception as e:
            print(f"❌ OpenAI analysis error: {e}")
            return self._mock_analysis(tweet_text, error=str(e))
    
    def _mock_analysis(self, tweet_text, error=None):
        """Generate mock analysis when OpenAI is not available"""
        # Simple keyword-based mock analysis
        text_lower = tweet_text.lower()
        
        # Basic keyword detection
        hateful_keywords = ['hate', 'stupid', 'idiot', 'kill', 'die']
        violent_keywords = ['violence', 'fight', 'attack', 'bomb', 'war']
        anti_america_keywords = ['america sucks', 'hate america', 'destroy america']
        
        hateful = any(keyword in text_lower for keyword in hateful_keywords)
        violent = any(keyword in text_lower for keyword in violent_keywords)
        anti_america = any(keyword in text_lower for keyword in anti_america_keywords)
        
        severity = "high" if (hateful or violent or anti_america) else "none"
        explanation = f"Mock analysis: {'Potentially problematic content detected' if (hateful or violent or anti_america) else 'No problematic content detected'}"
        
        if error:
            explanation += f" (OpenAI error: {error[:30]}...)"
        
        return {
            "hateful": hateful,
            "violent": violent,
            "anti_america": anti_america,
            "confidence": "medium",
            "explanation": explanation,
            "severity": severity
        }

def generate_mock_tweets(username, num_tweets):
    """
    Generate mock tweets for demonstration
    """
    mock_tweets = [
        f"Just had an amazing day! Life is good 😊 #{username}",
        "Technology is advancing so fast these days. What do you think about AI?",
        "Beautiful sunset today. Nature never fails to amaze me 🌅",
        "Working on some exciting new projects. Can't wait to share!",
        "Coffee and coding - the perfect combination ☕💻",
        "Reading an interesting book about history. Learning so much!",
        "Weekend plans: hiking with friends 🥾",
        "Grateful for all the opportunities coming my way",
        "Music has the power to change your mood instantly 🎵",
        "Thinking about travel destinations for next year ✈️",
        "Sometimes people can be really stupid and hateful",  # This will trigger analysis
        "Great weather for outdoor activities today!",
        "Learning new programming languages is challenging but fun",
        "Family time is the best time 👨‍👩‍👧‍👦",
        "Can't believe how fast this year is going by"
    ]
    
    # Return the requested number of tweets (cycle through if needed)
    selected_tweets = []
    for i in range(num_tweets):
        selected_tweets.append(mock_tweets[i % len(mock_tweets)])
    
    return selected_tweets

def analyze_tweets(username, num_tweets=10):
    """
    Analyze tweets for problematic content (using mock tweets)
    """
    try:
        print(f"🔍 Starting analysis for @{username} ({num_tweets} tweets)")
        
        # Get mock tweets (replace with real Twitter API integration when available)
        tweets = generate_mock_tweets(username, num_tweets)
        print(f"✅ Generated {len(tweets)} mock tweets")
        
        if not tweets:
            print("❌ No tweets found")
            return [], None
        
        # Initialize analyzer
        analyzer = TweetAnalyzer(OPENAI_API_KEY)
        
        results = []
        
        for i, tweet_text in enumerate(tweets, 1):
            print(f"🤖 Analyzing tweet {i}/{len(tweets)}: {tweet_text[:50]}...")
            # Analyze tweet
            analysis = analyzer.analyze_tweet(tweet_text)
            
            if analysis:
                tweet_data = {
                    "tweet_id": f"mock_{username}_{i}",
                    "tweet_text": tweet_text,
                    "created_at": datetime.now().isoformat(),
                    "analysis": analysis
                }
                results.append(tweet_data)
            
            # Small delay to simulate processing
            time.sleep(0.1)
        
        print(f"✅ Analysis complete! Processed {len(results)} tweets")
        
        # Mock user info
        user_info = {
            "name": f"Demo User ({username})",
            "screen_name": username,
            "id": f"demo_user_{username}"
        }
        
        return results, user_info
        
    except Exception as e:
        print(f"❌ Error in analyze_tweets: {e}")
        import traceback
        traceback.print_exc()
        return [], None

def generate_summary(results):
    """
    Generate summary statistics
    """
    if not results:
        return {
            'total_tweets': 0,
            'flagged_count': 0,
            'flagged_percentage': 0,
            'hateful_count': 0,
            'hateful_percentage': 0,
            'violent_count': 0,
            'violent_percentage': 0,
            'anti_america_count': 0,
            'anti_america_percentage': 0,
            'flagged_tweets': []
        }
    
    total_tweets = len(results)
    hateful_count = sum(1 for r in results if r['analysis']['hateful'])
    violent_count = sum(1 for r in results if r['analysis']['violent'])
    anti_america_count = sum(1 for r in results if r['analysis']['anti_america'])
    flagged_count = sum(1 for r in results if any([
        r['analysis']['hateful'], 
        r['analysis']['violent'], 
        r['analysis']['anti_america']
    ]))
    
    flagged_tweets = [r for r in results if any([
        r['analysis']['hateful'], 
        r['analysis']['violent'], 
        r['analysis']['anti_america']
    ])]
    
    return {
        'total_tweets': total_tweets,
        'flagged_count': flagged_count,
        'flagged_percentage': round(flagged_count/total_tweets*100, 1) if total_tweets > 0 else 0,
        'hateful_count': hateful_count,
        'hateful_percentage': round(hateful_count/total_tweets*100, 1) if total_tweets > 0 else 0,
        'violent_count': violent_count,
        'violent_percentage': round(violent_count/total_tweets*100, 1) if total_tweets > 0 else 0,
        'anti_america_count': anti_america_count,
        'anti_america_percentage': round(anti_america_count/total_tweets*100, 1) if total_tweets > 0 else 0,
        'flagged_tweets': flagged_tweets
    }

# Routes
@app.route('/')
def index():
    try:
        print("📍 Homepage route accessed")
        return render_template('index.html')
    except Exception as e:
        print(f"❌ Error loading index template: {e}")
        return f"""
        <h1>🐦 Twitter Content Analyzer</h1>
        <p>⚠️ Template error: {e}</p>
        <p><a href="/test">Test Route</a> | <a href="/health">Health Check</a></p>
        <style>body {{ font-family: Arial; padding: 50px; text-align: center; }}</style>
        """

@app.route('/test')
def test():
    return """
    <h1>🎉 Flask is Working!</h1>
    <p>✅ App is running successfully</p>
    <p>✅ Routes are working</p>
    <p>✅ Templates: Check <a href="/">Homepage</a></p>
    <p>✅ API: Check <a href="/health">Health</a></p>
    <p>✅ Debug: Check <a href="/debug">Debug Info</a></p>
    <style>
        body { font-family: Arial; padding: 50px; text-align: center; }
        h1 { color: #1da1f2; }
        a { color: #1da1f2; text-decoration: none; margin: 0 10px; }
    </style>
    """

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'message': 'Twitter Content Analyzer is running',
        'version': '1.0.0',
        'openai_available': OPENAI_AVAILABLE,
        'openai_key_set': bool(OPENAI_API_KEY),
        'mode': 'demo' if not OPENAI_AVAILABLE else 'full'
    })

@app.route('/debug')
def debug():
    try:
        import os
        files = []
        for root, dirs, filenames in os.walk('.'):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        
        return f"""
        <h1>🔧 Debug Information</h1>
        <h2>Environment Variables:</h2>
        <ul>
            <li>USERNAME: {USERNAME}</li>
            <li>EMAIL: {EMAIL}</li>
            <li>OPENAI_API_KEY: {'✅ Set' if OPENAI_API_KEY else '❌ Not Set'}</li>
            <li>PORT: {os.environ.get('PORT', 'Not Set')}</li>
            <li>OPENAI_AVAILABLE: {OPENAI_AVAILABLE}</li>
        </ul>
        
        <h2>Files in project:</h2>
        <ul style="text-align: left; max-width: 600px; margin: 0 auto;">
            {''.join([f'<li>{file}</li>' for file in sorted(files)])}
        </ul>
        
        <p><a href='/'>Home</a> | <a href='/test'>Test</a> | <a href='/health'>Health</a></p>
        
        <style>
            body {{ font-family: Arial; padding: 30px; text-align: center; }}
            h1, h2 {{ color: #1da1f2; }}
            ul {{ text-align: left; }}
            a {{ color: #1da1f2; text-decoration: none; margin: 0 10px; }}
        </style>
        """
    except Exception as e:
        return f"Debug error: {e}"

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        print("📍 Analyze route accessed")
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400
        
        username = data.get('username', '').strip()
        num_tweets = int(data.get('num_tweets', 10))
        
        print(f"📊 Analyzing: username={username}, num_tweets={num_tweets}")
        
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
        
        # Analyze tweets (using mock implementation)
        results, user_info = analyze_tweets(username, num_tweets)
        
        if not results:
            return jsonify({'error': f'Could not analyze tweets for @{username}. This is a demo version with mock data.'}), 404
        
        # Generate summary
        summary = generate_summary(results)
        
        # Save results in memory cache
        analysis_id = str(uuid.uuid4())
        analysis_cache[analysis_id] = {
            'username': username,
            'results': results,
            'summary': summary,
            'timestamp': datetime.now().isoformat(),
            'user_info': user_info
        }
        
        print(f"✅ Analysis completed for {username}, saved with ID: {analysis_id}")
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'username': username,
            'summary': summary,
            'user_info': user_info
        })
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/results/<analysis_id>')
def results(analysis_id):
    try:
        print(f"📍 Results route accessed for ID: {analysis_id}")
        
        if analysis_id not in analysis_cache:
            return f"""
            <h1>❌ Analysis Not Found</h1>
            <p>Analysis ID '{analysis_id}' not found in cache.</p>
            <p><a href='/'>← Back to Home</a></p>
            <style>body {{ font-family: Arial; padding: 50px; text-align: center; }}</style>
            """, 404
        
        data = analysis_cache[analysis_id]
        return render_template('results.html', 
                             username=data['username'],
                             summary=data['summary'],
                             results=data['results'],
                             user_info=data['user_info'],
                             timestamp=data['timestamp'])
    except Exception as e:
        print(f"❌ Results template error: {e}")
        return f"""
        <h1>❌ Results Error</h1>
        <p>Error loading results: {e}</p>
        <p><a href='/'>← Back to Home</a></p>
        <style>body {{ font-family: Arial; padding: 50px; text-align: center; }}</style>
        """

@app.route('/api/results/<analysis_id>')
def api_results(analysis_id):
    if analysis_id not in analysis_cache:
        return jsonify({'error': 'Analysis not found'}), 404
    
    return jsonify(analysis_cache[analysis_id])

@app.route('/api/cache-status')
def cache_status():
    """Show cache status for debugging"""
    return jsonify({
        'twitter_client_logged_in': client_logged_in,
        'cached_users': list(user_cache.keys()),
        'cached_analyses': len(analysis_cache),
        'analysis_ids': list(analysis_cache.keys()),
        'openai_available': OPENAI_AVAILABLE,
        'openai_key_set': bool(OPENAI_API_KEY)
    })

@app.route('/api/clear-cache')
def clear_cache():
    """Clear all caches (for debugging)"""
    global twitter_client, client_logged_in, user_cache, analysis_cache
    
    twitter_client = None
    client_logged_in = False
    user_cache.clear()
    analysis_cache.clear()
    
    return jsonify({'message': 'All caches cleared'})

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return f"""
    <h1>🔍 Page Not Found</h1>
    <p>The page you're looking for doesn't exist.</p>
    <p><a href='/'>← Back to Home</a> | <a href='/test'>Test Page</a></p>
    <style>body {{ font-family: Arial; padding: 50px; text-align: center; }}</style>
    """, 404

@app.errorhandler(500)
def internal_error(error):
    return f"""
    <h1>💥 Server Error</h1>
    <p>Something went wrong on our end.</p>
    <p><a href='/'>← Back to Home</a> | <a href='/health'>Health Check</a></p>
    <style>body {{ font-family: Arial; padding: 50px; text-align: center; }}</style>
    """, 500

if __name__ == '__main__':
    print("🚀 Starting Flask app...")
    print("💡 Visit /test for a working test page")
    print("💡 Visit /debug for debugging information")
    print("💡 Visit /health for health check")
    
    # Use environment variable for port (Render sets this)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
