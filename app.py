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
import sys

app = Flask(__name__)
# Enable CORS for all routes
CORS(app)

# Global variables for streaming output
output_queue = queue.Queue()

def print_simple_progress(process, url_index, url):
    """Print only progress bar to console in one line"""
    try:
        current_progress = 0
        video_title = "Unknown"
        
        # Create a thread to read output
        def read_output():
            nonlocal current_progress, video_title
            for line in iter(process.stdout.readline, b''):
                if line:
                    decoded_line = line.decode('utf-8', errors='replace').strip()
                    
                    # Extract video title for display
                    title_match = re.search(r'\[youtube\] (.+): Downloading webpage', decoded_line)
                    if title_match:
                        video_title = title_match.group(1)[:50]  # Truncate long titles
                    
                    # Only process progress lines for console display
                    if '[download]' in decoded_line and '%' in decoded_line:
                        # Extract progress information
                        progress_match = re.search(r'\[download\]\s+(\d+(?:\.\d+)?)%', decoded_line)
                        if progress_match:
                            current_progress = float(progress_match.group(1))
                            
                            # Extract additional info if available
                            size_match = re.search(r'of\s+([\d.]+\s+[KMGT]?iB)', decoded_line)
                            speed_match = re.search(r'at\s+([\d.]+\s+[KMGT]?iB/s)', decoded_line)
                            eta_match = re.search(r'ETA\s+([\d:]+)', decoded_line)
                            
                            size = size_match.group(1) if size_match else "Unknown"
                            speed = speed_match.group(1) if speed_match else "Unknown"
                            eta = eta_match.group(1) if eta_match else "Unknown"
                            
                            # Create a clean, one-line progress bar
                            bar_length = 30
                            filled_length = int(bar_length * current_progress / 100)
                            bar = '█' * filled_length + '░' * (bar_length - filled_length)
                            
                            # Print progress bar with carriage return to overwrite
                            progress_line = f"[URL {url_index + 1}] {video_title}: {current_progress:5.1f}% |{bar}| {size} @ {speed} ETA: {eta}"
                            sys.stdout.write(f'\r{progress_line}')
                            sys.stdout.flush()
                    
                    # Send all output to web interface
                    output_queue.put({
                        'type': 'log',
                        'message': decoded_line,
                        'url_index': url_index,
                        'url': url,
                        'progress': current_progress
                    })
            
            # Clear the progress line when done
            sys.stdout.write('\r' + ' ' * 100 + '\r')
            sys.stdout.flush()
            
            process.wait()
            
            # Print final status
            if process.returncode == 0:
                print(f"[URL {url_index + 1}] ✓ {video_title} - Complete!")
                output_queue.put({
                    'type': 'complete',
                    'url_index': url_index,
                    'url': url,
                    'return_code': 0,
                    'progress': 100
                })
            else:
                print(f"[URL {url_index + 1}] ✗ {video_title} - Failed!")
                output_queue.put({
                    'type': 'complete',
                    'url_index': url_index,
                    'url': url,
                    'return_code': process.returncode,
                    'progress': current_progress
                })
        
        # Start reading output in a separate thread
        output_thread = threading.Thread(target=read_output)
        output_thread.daemon = True
        output_thread.start()
        output_thread.join()
        
    except Exception as e:
        print(f"[URL {url_index + 1}] ✗ Error: {str(e)}")
        output_queue.put({
            'type': 'error',
            'message': str(e),
            'url_index': url_index,
            'url': url,
            'progress': current_progress
        })

def run_with_retry(cmd, url_index, url, max_retries=3):
    """Run a command with retry logic and exponential backoff"""
    retry_count = 0
    base_delay = 2  # Base delay in seconds
    
    while retry_count < max_retries:
        try:
            # Add random delay to avoid detection
            delay = base_delay * (2 ** retry_count) + random.uniform(0.5, 1.5)
            if retry_count > 0:
                print(f"[URL {url_index + 1}] Retrying in {delay:.1f} seconds... (Attempt {retry_count + 1}/{max_retries})")
                output_queue.put({
                    'type': 'log',
                    'message': f"Retrying in {delay:.1f} seconds... (Attempt {retry_count + 1}/{max_retries})",
                    'url_index': url_index,
                    'url': url,
                    'progress': 0
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
                text=False,
                bufsize=1,
                universal_newlines=False
            )
            
            # Print only progress bar
            print_simple_progress(process, url_index, url)
            
            # Return the process return code
            return process.returncode
        
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f"[URL {url_index + 1}] Error occurred: {str(e)}. Retrying...")
                output_queue.put({
                    'type': 'warning',
                    'message': f"Error occurred: {str(e)}. Retrying...",
                    'url_index': url_index,
                    'url': url,
                    'progress': 0
                })
    
    # All retries failed
    print(f"[URL {url_index + 1}] ✗ Failed after {max_retries} attempts")
    output_queue.put({
        'type': 'error',
        'message': f"Failed after {max_retries} attempts",
        'url_index': url_index,
        'url': url,
        'progress': 0
    })
    return 1

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
        
        print(f"\n{'='*60}")
        print(f"Downloading {len(urls)} video(s)")
        print(f"{'='*60}\n")
        
        # Clear the output queue
        while not output_queue.empty():
            output_queue.get()
        
        # Start a thread for each URL
        for i, url in enumerate(urls):
            def start_download(url_index, url_string):
                try:
                    # Build the command
                    cmd = ['yt-dlp.exe']
                    cmd.extend(['--ignore-config', '--continue', '--no-overwrites', '--mtime'])
                    
                    # Add rate limiting options
                    cmd.extend(['--rate-limit', '1M'])  # Limit download rate
                    cmd.extend(['--retries', '10'])     # Increase retry count
                    cmd.extend(['--fragment-retries', '10'])  # Retry failed fragments
                    
                    # Add console output options
                    cmd.extend(['--no-colors'])  # Remove colors for cleaner console output
                    
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
                    cmd.append(url_string)
                    
                    # First attempt to download with subtitles
                    return_code = run_with_retry(cmd, url_index, url_string)
                    
                    # If subtitle download failed, try without subtitles
                    if return_code != 0 and subtitle_options:
                        print(f"[URL {url_index + 1}] Subtitle download failed, retrying without subtitles...")
                        output_queue.put({
                            'type': 'warning',
                            'message': "Subtitle download failed, retrying without subtitles...",
                            'url_index': url_index,
                            'url': url_string,
                            'progress': 0
                        })
                        
                        # Create a new command without subtitle options
                        cmd_no_subs = [arg for arg in cmd if arg not in subtitle_options]
                        
                        # Try again without subtitles
                        return_code = run_with_retry(cmd_no_subs, url_index, url_string)
                    
                    # Send final status to web interface
                    if return_code == 0:
                        output_queue.put({
                            'type': 'log',
                            'message': f"Successfully downloaded: {url_string}",
                            'url_index': url_index,
                            'url': url_string,
                            'progress': 100
                        })
                    else:
                        output_queue.put({
                            'type': 'error',
                            'message': f"Failed to download: {url_string}",
                            'url_index': url_index,
                            'url': url_string,
                            'progress': 0
                        })
                
                except Exception as e:
                    print(f"[URL {url_index + 1}] ✗ Error processing {url_string}: {str(e)}")
                    output_queue.put({
                        'type': 'error',
                        'message': f"Error processing {url_string}: {str(e)}",
                        'url_index': url_index,
                        'url': url_string,
                        'progress': 0
                    })
            
            # Start each download with a small delay to avoid overwhelming the server
            thread = threading.Thread(target=start_download, args=(i, url))
            thread.daemon = True
            thread.start()
            time.sleep(1)  # Delay between starting downloads for better console visibility
        
        return jsonify({'success': True, 'message': 'Downloads started'})
    except Exception as e:
        print(f"Error starting downloads: {str(e)}")
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
        
        print("\n" + "="*60)
        print("Updating yt-dlp...")
        print("="*60 + "\n")
        
        process = subprocess.Popen(
            ['yt-dlp.exe', '--update'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # Print update output to console
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.strip())
        
        output, error = process.communicate()
        
        if process.returncode == 0:
            print("\n✓ yt-dlp updated successfully!")
            return jsonify({'success': True, 'message': 'yt-dlp updated successfully'})
        else:
            print(f"\n✗ Update failed: {output}")
            return jsonify({'success': False, 'error': output})
    except Exception as e:
        print(f"\n✗ Update error: {str(e)}")
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
            print(f"Cookie file uploaded successfully: {filepath}")
            return jsonify({'success': True, 'message': 'Cookie file uploaded successfully'})
        else:
            return jsonify({'success': False, 'error': 'Invalid file format. Please upload a .txt file'}), 400
    except Exception as e:
        print(f"Cookie upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    print("\n" + "="*60)
    print("   YouTube Downloader GUI Server")
    print("="*60)
    print("Server starting on http://localhost:5000")
    print("Press Ctrl+C to stop the server")
    print("="*60 + "\n")
    
    try:
        app.run(debug=False, port=5000)  # Disabled debug to avoid duplicate output
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\n\nServer error: {str(e)}")