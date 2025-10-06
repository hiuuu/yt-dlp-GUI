from flask import Flask, request, jsonify, Response, send_from_directory
from flask_cors import CORS
import subprocess
import json
import os
import threading
import queue
import time
import re
import tempfile
import random

app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

# Global variables for streaming output
output_queue = queue.Queue()

def stream_output(process, url_index):
    """Stream output from yt-dlp process to a queue"""
    try:
        for line in iter(process.stdout.readline, b''):
            if line:
                decoded_line = line.decode('utf-8', errors='replace').strip()
                output_queue.put({
                    'type': 'log',
                    'message': decoded_line,
                    'url_index': url_index
                })
        
        process.wait()
        output_queue.put({
            'type': 'complete',
            'url_index': url_index,
            'return_code': process.returncode
        })
    except Exception as e:
        output_queue.put({
            'type': 'error',
            'message': str(e),
            'url_index': url_index
        })

def run_with_retry(cmd, url_index, max_retries=3):
    """Run a command with retry logic and exponential backoff"""
    retry_count = 0
    base_delay = 2  # Base delay in seconds
    
    while retry_count < max_retries:
        try:
            # Add random delay to avoid detection
            delay = base_delay * (2 ** retry_count) + random.uniform(0.5, 1.5)
            if retry_count > 0:
                output_queue.put({
                    'type': 'log',
                    'message': f"Retrying in {delay:.1f} seconds... (Attempt {retry_count + 1}/{max_retries})",
                    'url_index': url_index
                })
                time.sleep(delay)
            
            # Add random user agent to avoid detection
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36'
            ]
            
            # Add user agent to command
            cmd_with_ua = cmd + ['--user-agent', random.choice(user_agents)]
            
            # Run the process
            process = subprocess.Popen(
                cmd_with_ua,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False
            )
            
            # Stream output
            for line in iter(process.stdout.readline, b''):
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    output_queue.put({
                        'type': 'log',
                        'message': decoded_line,
                        'url_index': url_index
                    })
            
            process.wait()
            
            # Check if the process was successful
            if process.returncode == 0:
                return True
            else:
                retry_count += 1
                if retry_count < max_retries:
                    output_queue.put({
                        'type': 'warning',
                        'message': f"Command failed with return code {process.returncode}. Retrying...",
                        'url_index': url_index
                    })
        
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                output_queue.put({
                    'type': 'warning',
                    'message': f"Error occurred: {str(e)}. Retrying...",
                    'url_index': url_index
                })
    
    # All retries failed
    output_queue.put({
        'type': 'error',
        'message': f"Failed after {max_retries} attempts",
        'url_index': url_index
    })
    return False

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/download', methods=['POST', 'OPTIONS'])
def download():
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data received'}), 400
            
        urls = data.get('urls', [])
        options = data.get('options', {})
        
        if not urls:
            return jsonify({'success': False, 'error': 'No URLs provided'}), 400
        
        # Clear the output queue
        while not output_queue.empty():
            output_queue.get()
        
        # Start a thread for each URL
        for i, url in enumerate(urls):
            # Build the command
            cmd = ['yt-dlp.exe']
            cmd.extend(['--ignore-config', '--continue', '--no-overwrites', '--mtime'])
            
            # Add rate limiting options
            cmd.extend(['--rate-limit', '1M'])  # Limit download rate
            cmd.extend(['--retries', '10'])     # Increase retry count
            cmd.extend(['--fragment-retries', '10'])  # Retry failed fragments
            
            # Add authentication settings
            auth = options.get('authentication', {})
            if auth.get('enabled'):
                method = auth.get('method')
                
                if method == 'browser' and auth.get('browser'):
                    # Browser cookies authentication
                    browser = auth.get('browser')
                    cmd.extend(['--cookies-from-browser', browser])
                    
                    if auth.get('profile'):
                        cmd.extend(['--cookies-from-browser', f"{browser}:{auth.get('profile')}"])
                
                elif method == 'manual' and auth.get('username') and auth.get('password'):
                    # Manual login authentication
                    cmd.extend(['--username', auth.get('username')])
                    cmd.extend(['--password', auth.get('password')])
                    
                    if auth.get('twoFactor'):
                        cmd.extend(['--twofactor', auth.get('twoFactor')])
                
                elif method == 'file' and auth.get('cookieFile'):
                    # Cookie file authentication
                    # In a real implementation, you would handle file upload
                    # For now, we'll assume the file is in the same directory
                    cookie_file_path = os.path.join(os.getcwd(), auth.get('cookieFile'))
                    if os.path.exists(cookie_file_path):
                        cmd.extend(['--cookies', cookie_file_path])
            
            # Add proxy settings
            proxy = options.get('proxy', {})
            if proxy.get('enabled'):
                proxy_url = f"{proxy['type']}://"
                if proxy.get('username') and proxy.get('password'):
                    proxy_url += f"{proxy['username']}:{proxy['password']}@"
                proxy_url += f"{proxy['host']}:{proxy['port']}"
                cmd.extend(['--proxy', proxy_url])
                
                if proxy.get('bypass'):
                    cmd.extend(['--proxy-bypass', proxy['bypass']])
            
            # Add format/quality options
            quality = options.get('quality')
            if quality:
                cmd.extend(['-f', quality])
            
            # Add output format
            format_type = options.get('format')
            if format_type:
                if format_type in ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']:
                    cmd.extend(['-x', '--audio-format', format_type])
                else:
                    cmd.extend(['--merge-output-format', format_type])
            
            # Add subtitle options with better error handling
            subtitle_options = []
            if options.get('writeSub') or options.get('embedSubs') or options.get('persianSubs'):
                # Get subtitle format (default to srt)
                sub_format = options.get('subtitleFormat', 'srt')
                
                # Build subtitle languages list
                langs = []
                if options.get('subtitleLangs'):
                    langs.extend([lang.strip() for lang in options.get('subtitleLangs').split(',')])
                
                # Add Persian if requested
                if options.get('persianSubs'):
                    langs.append('fa')
                    # Also try auto-generated Persian
                    langs.append('fa-auto')
                
                # Remove duplicates
                langs = list(set(langs))
                
                if langs:
                    cmd.extend(['--sub-langs', ','.join(langs)])
                
                if options.get('writeSub'):
                    cmd.append('--write-sub')
                    cmd.append('--write-auto-sub')
                    # Force specified subtitle format
                    cmd.extend(['--sub-format', sub_format])
                    cmd.extend(['--convert-subs', sub_format])
                
                if options.get('embedSubs'):
                    cmd.append('--embed-subs')
                    # Also force specified format for embedded subtitles
                    cmd.extend(['--sub-format', sub_format])
                    cmd.extend(['--convert-subs', sub_format])
                
                # Store subtitle options for separate download if needed
                subtitle_options = ['--write-sub', '--write-auto-sub', '--sub-langs', ','.join(langs), '--sub-format', sub_format, '--convert-subs', sub_format]
            
            # Add additional options
            if options.get('embedThumb'):
                cmd.append('--embed-thumbnail')
            if options.get('writeDesc'):
                cmd.append('--write-description')
            if options.get('writeMeta'):
                cmd.append('--write-info-json')
            if options.get('writeComments'):
                cmd.append('--write-comments')
            if options.get('writeThumbnail'):
                cmd.append('--write-thumbnail')
            
            # Add output template
            if options.get('outputTemplate'):
                cmd.extend(['-o', options['outputTemplate']])
            
            # Add download path
            if options.get('downloadPath'):
                download_path = options['downloadPath']
                if not os.path.exists(download_path):
                    os.makedirs(download_path, exist_ok=True)
                cmd.extend(['-P', download_path])
            
            # Add the URL
            cmd.append(url)
            
            # Start the process in a thread
            def start_process():
                try:
                    # First attempt to download with subtitles
                    success = run_with_retry(cmd, i)
                    
                    # If subtitle download failed, try without subtitles
                    if not success and subtitle_options:
                        output_queue.put({
                            'type': 'warning',
                            'message': "Subtitle download failed, retrying without subtitles...",
                            'url_index': i
                        })
                        
                        # Create a new command without subtitle options
                        cmd_no_subs = [arg for arg in cmd if arg not in subtitle_options]
                        
                        # Try again without subtitles
                        success = run_with_retry(cmd_no_subs, i)
                    
                    if success:
                        output_queue.put({
                            'type': 'complete',
                            'url_index': i,
                            'return_code': 0
                        })
                    else:
                        output_queue.put({
                            'type': 'complete',
                            'url_index': i,
                            'return_code': 1
                        })
                
                except Exception as e:
                    output_queue.put({
                        'type': 'error',
                        'message': str(e),
                        'url_index': i
                    })
            
            thread = threading.Thread(target=start_process)
            thread.daemon = True
            thread.start()
        
        return jsonify({'success': True, 'message': 'Downloads started'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/stream', methods=['GET', 'OPTIONS'])
def stream():
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return '', 200
        
    def generate():
        while True:
            try:
                # Get message from queue with timeout
                message = output_queue.get(timeout=1)
                yield f"data: {json.dumps(message)}\n\n"
            except queue.Empty:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
    
    return Response(generate(), mimetype='text/event-stream')

@app.route('/update', methods=['POST', 'OPTIONS'])
def update():
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Check if yt-dlp.exe exists
        if not os.path.exists('yt-dlp.exe'):
            return jsonify({'success': False, 'error': 'yt-dlp.exe not found. Please make sure it is in the same directory as app.py.'})
        
        process = subprocess.Popen(
            ['yt-dlp.exe', '--update'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        output, error = process.communicate()
        
        if process.returncode == 0:
            return jsonify({'success': True, 'message': 'yt-dlp updated successfully'})
        else:
            return jsonify({'success': False, 'error': output})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/upload-cookie', methods=['POST', 'OPTIONS'])
def upload_cookie():
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        if 'cookieFile' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
        
        file = request.files['cookieFile']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if file and file.filename.endswith('.txt'):
            # Save the uploaded file
            filename = 'cookies.txt'
            filepath = os.path.join(os.getcwd(), filename)
            file.save(filepath)
            return jsonify({'success': True, 'message': 'Cookie file uploaded successfully'})
        else:
            return jsonify({'success': False, 'error': 'Invalid file format. Please upload a .txt file'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)