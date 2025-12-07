from flask import Flask, render_template, request, jsonify
import json
from scraper import YouTubeCommunityScraper
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
logging.basicConfig(level=logging.INFO)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/scrape', methods=['POST'])
def scrape_comments():
    try:
        data = request.get_json()
        community_url = data.get('url')
        
        if not community_url:
            return jsonify({'error': 'Please provide a YouTube Community URL'}), 400
        
        scraper = YouTubeCommunityScraper()
        comments = scraper.get_top_comments(community_url, limit=50)
        
        if 'error' in comments:
            return jsonify({'error': comments['error']}), 400
        
        return jsonify({
            'success': True,
            'comments': comments,
            'count': len(comments)
        })
        
    except Exception as e:
        logging.error(f"Error scraping comments: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/export', methods=['POST'])
def export_comments():
    try:
        data = request.get_json()
        comments = data.get('comments', [])
        
        # Format comments for copying
        formatted_text = "Top 50 Most Liked Comments:\n\n"
        for i, comment in enumerate(comments, 1):
            formatted_text += f"{i}. {comment['author']}:\n"
            formatted_text += f"   {comment['text']}\n"
            formatted_text += f"   👍 {comment['likes']} likes\n"
            formatted_text += f"   📅 {comment['timestamp']}\n"
            formatted_text += f"   🔗 {comment['comment_url']}\n"
            formatted_text += "-" * 50 + "\n"
        
        return jsonify({
            'success': True,
            'formatted_text': formatted_text
        })
        
    except Exception as e:
        logging.error(f"Error exporting comments: {str(e)}")
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)