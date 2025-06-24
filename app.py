from flask import Flask, render_template, request, jsonify
import asyncio
import openai
from twikit import Client
import json
import time
import os
import uuid
from datetime import datetime

app = Flask(__name__)

# In-memory storage for analysis results (simple alternative to sessions)
analysis_cache = {}

# Configuration
USERNAME = 'Codek37727'
EMAIL = 'codenahiphatega@gmail.com' 
PASSWORD = 'Foreign@2023'
OPENAI_API_KEY = 'your-openai-api-key-here'  # Replace with your key

class TweetAnalyzer:
    def __init__(self, openai_api_key):
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
    
    def analyze_tweet(self, tweet_text):
        """
        Analyze a single tweet for hateful, violent, or anti-America content
        """
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
            return {
                "hateful": False,
                "violent": False,
                "anti_america": False,
                "confidence": "low",
                "explanation": f"Analysis error: {str(e)[:50]}",
                "severity": "none"
            }

async def fetch_and_analyze_tweets(screen_name, num_tweets=20):
    """
    Fetch tweets and analyze them for problematic content
    """
    client = Client('en-US')
    
    try:
        print(f"Attempting to login with username: {USERNAME}")
        print(f"Email: {EMAIL}")
        print(f"Attempting to fetch tweets for: {screen_name}")
        
        # Login to Twitter
        await client.login(
            auth_info_1=USERNAME,
            auth_info_2=EMAIL,
            password=PASSWORD,
            cookies_file='cookies.json'
        )
        print("✅ Login successful!")
        
        # Get user by screen name
        print(f"Looking up user: {screen_name}")
        user = await client.get_user_by_screen_name(screen_name)
        user_id = user.id
        print(f"✅ Found user: {user.name} (@{user.screen_name}) - ID: {user_id}")
        
        # Fetch tweets
        print(f"Fetching {num_tweets} tweets...")
        tweets = await client.get_user_tweets(user_id, 'Tweets', count=num_tweets)
        print(f"✅ Fetched {len(tweets)} tweets")
        
        # Initialize analyzer
        analyzer = TweetAnalyzer(OPENAI_API_KEY)
        
        results = []
        
        for i, tweet in enumerate(tweets, 1):
            print(f"Analyzing tweet {i}/{len(tweets)}: {tweet.text[:50]}...")
            # Analyze tweet
            analysis = analyzer.analyze_tweet(tweet.text)
            
            if analysis:
                tweet_data = {
                    "tweet_id": tweet.id,
                    "tweet_text": tweet.text,
                    "created_at": tweet.created_at if hasattr(tweet, 'created_at') else None,
                    "analysis": analysis
                }
                results.append(tweet_data)
            
            # Rate limiting - increased delay
            time.sleep(2)  # Increased from 0.5 to 2 seconds
        
        print(f"✅ Analysis complete! Processed {len(results)} tweets")
        return results, user
        
    except Exception as e:
        print(f"❌ Error in fetch_and_analyze_tweets: {e}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return [], None

def generate_summary(results):
    """
    Generate summary statistics
    """
    if not results:
        return {}
    
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
        'flagged_percentage': round(flagged_count/total_tweets*100, 1),
        'hateful_count': hateful_count,
        'hateful_percentage': round(hateful_count/total_tweets*100, 1),
        'violent_count': violent_count,
        'violent_percentage': round(violent_count/total_tweets*100, 1),
        'anti_america_count': anti_america_count,
        'anti_america_percentage': round(anti_america_count/total_tweets*100, 1),
        'flagged_tweets': flagged_tweets
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    username = data.get('username', '').strip()
    num_tweets = int(data.get('num_tweets', 20))
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # Remove @ if present
    if username.startswith('@'):
        username = username[1:]
    
    try:
        # Run the async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        results, user = loop.run_until_complete(
            fetch_and_analyze_tweets(username, num_tweets)
        )
        
        loop.close()
        
        if not results:
            return jsonify({'error': f'Could not fetch tweets for @{username}. User may not exist or tweets may be private.'}), 404
        
        # Generate summary
        summary = generate_summary(results)
        
        # Save results in memory cache
        analysis_id = str(uuid.uuid4())
        analysis_cache[analysis_id] = {
            'username': username,
            'results': results,
            'summary': summary,
            'timestamp': datetime.now().isoformat(),
            'user_info': {
                'name': user.name if user else username,
                'screen_name': user.screen_name if user else username,
                'id': user.id if user else 'unknown'
            }
        }
        
        return jsonify({
            'success': True,
            'analysis_id': analysis_id,
            'username': username,
            'summary': summary,
            'user_info': analysis_cache[analysis_id]['user_info']
        })
        
    except Exception as e:
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500

@app.route('/results/<analysis_id>')
def results(analysis_id):
    if analysis_id not in analysis_cache:
        return "Analysis not found", 404
    
    data = analysis_cache[analysis_id]
    return render_template('results.html', 
                         username=data['username'],
                         summary=data['summary'],
                         results=data['results'],
                         user_info=data['user_info'],
                         timestamp=data['timestamp'])

@app.route('/api/results/<analysis_id>')
def api_results(analysis_id):
    if analysis_id not in analysis_cache:
        return jsonify({'error': 'Analysis not found'}), 404
    
    return jsonify(analysis_cache[analysis_id])

@app.route('/api/cache-status')
def cache_status():
    """
    Show cache status for debugging
    """
    return jsonify({
        'twitter_client_logged_in': client_logged_in,
        'cached_users': list(user_cache.keys()),
        'cached_analyses': len(analysis_cache),
        'analysis_ids': list(analysis_cache.keys())
    })

@app.route('/api/clear-cache')
def clear_cache():
    """
    Clear all caches (for debugging)
    """
    global twitter_client, client_logged_in, user_cache, analysis_cache
    
    twitter_client = None
    client_logged_in = False
    user_cache.clear()
    analysis_cache.clear()
    
    return jsonify({'message': 'All caches cleared'})

if __name__ == '__main__':
    print("🚀 Starting Flask app...")
    print("💡 Tip: Visit /api/cache-status to see cache status")
    print("💡 Tip: Visit /api/clear-cache to clear all caches")
    
    # Use environment variable for port (for hosting platforms)
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)