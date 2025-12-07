import requests
from bs4 import BeautifulSoup
import re
import json
from typing import List, Dict, Optional
import time
from urllib.parse import urlparse, parse_qs

class YouTubeCommunityScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })
        self.base_url = "https://www.youtube.com"
    
    def extract_post_id(self, url: str) -> Optional[str]:
        """Extract community post ID from URL"""
        patterns = [
            r'post/([a-zA-Z0-9_-]+)',
            r'community\?lb=([a-zA-Z0-9_-]+)',
            r'community/post/([a-zA-Z0-9_-]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_comments_data(self, post_id: str) -> List[Dict]:
        """Fetch and parse comments from YouTube community post"""
        comments = []
        
        try:
            # First, try to get the post page
            post_url = f"{self.base_url}/post/{post_id}"
            response = self.session.get(post_url)
            
            if response.status_code != 200:
                # Alternative URL format
                post_url = f"{self.base_url}/channel/community?lb={post_id}"
                response = self.session.get(post_url)
            
            if response.status_code != 200:
                return {'error': 'Failed to fetch community post. Check the URL.'}
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for comment data in script tags
            scripts = soup.find_all('script')
            comment_data = None
            
            for script in scripts:
                if script.string and 'commentThreadsRenderer' in script.string:
                    # Try to extract JSON data
                    text = script.string
                    # Look for ytInitialData pattern
                    patterns = [
                        r'ytInitialData\s*=\s*({.+?});',
                        r'var ytInitialData\s*=\s*({.+?});'
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, text, re.DOTALL)
                        if match:
                            try:
                                data = json.loads(match.group(1))
                                comment_data = self.extract_comments_from_data(data)
                                if comment_data:
                                    comments.extend(comment_data)
                            except json.JSONDecodeError:
                                continue
            
            # If no comments found in scripts, try alternative approach
            if not comments:
                comments = self.extract_comments_alternative(soup)
            
            # Sort by likes and get top 50
            comments.sort(key=lambda x: x.get('likes', 0), reverse=True)
            return comments[:50]
            
        except Exception as e:
            return {'error': f'Error fetching comments: {str(e)}'}
    
    def extract_comments_from_data(self, data: Dict) -> List[Dict]:
        """Extract comments from YouTube's data structure"""
        comments = []
        
        def search_comments(obj):
            if isinstance(obj, dict):
                if 'commentThreadsRenderer' in obj:
                    thread = obj['commentThreadsRenderer']
                    comment_renderer = thread.get('comment', {}).get('commentRenderer', {})
                    
                    # Extract comment details
                    text_elements = comment_renderer.get('contentText', {}).get('runs', [])
                    comment_text = ''.join([elem.get('text', '') for elem in text_elements])
                    
                    author = comment_renderer.get('authorText', {}).get('simpleText', '')
                    likes = comment_renderer.get('voteCount', {}).get('simpleText', '0')
                    
                    # Convert likes to integer
                    likes_int = 0
                    if likes:
                        likes = likes.replace(',', '')
                        if 'K' in likes:
                            likes_int = int(float(likes.replace('K', '')) * 1000)
                        elif 'M' in likes:
                            likes_int = int(float(likes.replace('M', '')) * 1000000)
                        else:
                            likes_int = int(likes) if likes.isdigit() else 0
                    
                    comment_id = comment_renderer.get('commentId', '')
                    comment_url = f"{self.base_url}/comment/{comment_id}" if comment_id else ""
                    
                    timestamp = comment_renderer.get('publishedTimeText', {}).get('runs', [{}])[0].get('text', '')
                    
                    if comment_text and author:
                        comments.append({
                            'author': author,
                            'text': comment_text,
                            'likes': likes_int,
                            'timestamp': timestamp,
                            'comment_url': comment_url,
                            'comment_id': comment_id
                        })
                
                for key, value in obj.items():
                    search_comments(value)
            
            elif isinstance(obj, list):
                for item in obj:
                    search_comments(item)
        
        search_comments(data)
        return comments
    
    def extract_comments_alternative(self, soup: BeautifulSoup) -> List[Dict]:
        """Alternative method to extract comments if primary fails"""
        comments = []
        
        # Look for comment elements
        comment_elements = soup.find_all('div', {'id': re.compile(r'comment-')})
        
        for element in comment_elements:
            try:
                # Extract author
                author_elem = element.find('a', {'id': 'author-text'})
                author = author_elem.text.strip() if author_elem else "Unknown"
                
                # Extract comment text
                text_elem = element.find('div', {'id': 'content-text'})
                comment_text = text_elem.text.strip() if text_elem else ""
                
                # Extract likes
                likes_elem = element.find('span', {'id': re.compile(r'vote-count-')})
                likes_text = likes_elem.text.strip() if likes_elem else "0"
                
                # Convert likes
                likes_int = 0
                if likes_text:
                    likes_text = likes_text.replace(',', '')
                    if 'K' in likes_text:
                        likes_int = int(float(likes_text.replace('K', '')) * 1000)
                    elif 'M' in likes_text:
                        likes_int = int(float(likes_text.replace('M', '')) * 1000000)
                    else:
                        likes_int = int(likes_text) if likes_text.replace('.', '').isdigit() else 0
                
                # Extract timestamp
                time_elem = element.find('yt-formatted-string', {'class': 'published-time-text'})
                timestamp = time_elem.text.strip() if time_elem else ""
                
                # Extract comment ID
                comment_id = element.get('id', '').replace('comment-', '')
                comment_url = f"{self.base_url}/comment/{comment_id}" if comment_id else ""
                
                if comment_text:
                    comments.append({
                        'author': author,
                        'text': comment_text,
                        'likes': likes_int,
                        'timestamp': timestamp,
                        'comment_url': comment_url,
                        'comment_id': comment_id
                    })
                    
            except Exception as e:
                continue
        
        return comments
    
    def get_top_comments(self, url: str, limit: int = 50) -> List[Dict]:
        """Main method to get top comments"""
        post_id = self.extract_post_id(url)
        
        if not post_id:
            return {'error': 'Invalid YouTube Community URL. Please check the URL format.'}
        
        comments = self.get_comments_data(post_id)
        
        if isinstance(comments, dict) and 'error' in comments:
            return comments
        
        # Ensure we have comments and sort by likes
        if comments:
            comments.sort(key=lambda x: x.get('likes', 0), reverse=True)
            return comments[:limit]
        
        return {'error': 'No comments found. The post might not have comments or the format has changed.'}

# Example usage
if __name__ == "__main__":
    scraper = YouTubeCommunityScraper()
    
    # Test with a YouTube community post URL
    test_url = "https://www.youtube.com/post/YOUR_POST_ID_HERE"
    comments = scraper.get_top_comments(test_url, limit=5)
    
    if isinstance(comments, list):
        for i, comment in enumerate(comments, 1):
            print(f"{i}. {comment['author']}: {comment['text'][:100]}...")
            print(f"   👍 {comment['likes']} likes")
            print()
    else:
        print(f"Error: {comments.get('error', 'Unknown error')}")