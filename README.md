

# YT Downloader GUI

A modern, feature-rich web-based YT downloader built with Flask and yt-dlp. Download videos, audio, and subtitles with advanced options including authentication, proxy support.

![Python](https://img.shields.io/badge/Python-3.6+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0+-green?style=for-the-badge&logo=flask)

## 🌟 Features

- **Modern Web Interface**: Clean, responsive dark theme UI
- **Multiple Download Options**: Video, audio-only, and various formats
- **Advanced Format Selection**: Manual format strings with presets
- **Subtitle Support**: Download subtitles in SRT format (default) with Persian auto-generated subtitle support
- **Authentication Options**: Browser cookies, manual login, or cookie file authentication
- **Proxy Support**: HTTP, HTTPS, SOCKS4, and SOCKS5 proxies with authentication
- **Retry Logic**: Automatic retry with exponential backoff for failed downloads
- **Batch Downloads**: Download multiple URLs simultaneously
- **Real-time Progress**: Live download progress and console output
- **Persistent Settings**: All preferences are saved automatically

## 📋 Requirements

- **Python 3.6 or higher**
- **yt-dlp.exe** (must be placed in the same directory as app.py)
- **Required Python packages**:
  - Flask
  - Flask-CORS

## 🚀 Installation

### 1. Clone or Download the Repository

```bash
git clone https://github.com/hiuuu/yt-dlp-GUI.git
cd yt-dlp-GUI
```

### 2. Install Python

Download and install Python from [python.org](https://www.python.org/downloads/). Make sure to check **"Add Python to PATH"** during installation.

### 3. Install Required Packages

```bash
pip install flask flask-cors
```

### 4. Download yt-dlp.exe

**IMPORTANT**: You must download `yt-dlp.exe` and place it in the same directory as `app.py`.

1. Go to the [yt-dlp releases page](https://github.com/yt-dlp/yt-dlp/releases)
2. Download the latest `yt-dlp.exe` file for Windows
3. Save it in the same folder as `app.py`

Your project structure should look like this:
```
youtube-downloader-gui/
├── app.py              # Python backend
├── index.html          # HTML frontend
├── run.bat             # Windows batch file to run the app
├── yt-dlp.exe          # yt-dlp executable (you must download this)
└── README.md           # This file
```

**IMPORTANT**: yt-dlp needs to have access ffmpeg and ffprobe refers on [yt-dlp github page](https://github.com/yt-dlp/yt-dlp/)

## 🎯 Quick Start

### Option 1: Using run.bat (Windows)

1. Double-click `run.bat` to start the application
2. Firefox will automatically open with the application
3. If Firefox is not found, your default browser will be used

### Option 2: Manual Start

1. Open Command Prompt or Terminal
2. Navigate to the project directory
3. Run:
   ```bash
   python app.py
   ```
4. Open your browser and go to `http://localhost:5000`

## 📖 Usage Guide

### Basic Download

1. **Add URLs**: Enter YouTube URLs in the text area, one per line
2. **Select Quality**: Choose from preset quality options or use advanced format selection
3. **Choose Format**: Select output format (MP4, MP3, etc.)
4. **Set Download Path**: Choose where to save your downloads
5. **Click Download**: Start the download process

### Advanced Features

#### Subtitles
- Enable "Write Subtitles" to download subtitle files
- Check "Persian Subtitles" for auto-generated Persian subtitles
- Select subtitle format (SRT recommended)
- Specify multiple languages (e.g., `en,fa,es`)

#### Authentication
For age-restricted or private content:
1. Go to the **Auth** tab
2. Enable authentication
3. Choose method:
   - **Browser Cookies**: Import from Chrome, Firefox, Edge, etc.
   - **Manual Login**: Enter username and password
   - **Cookie File**: Upload a cookies.txt file

#### Proxy Settings
1. Go to the **Proxy** tab
2. Enable proxy
3. Configure proxy type, host, and port
4. Add authentication if required

#### Advanced Format Selection
1. Click "Advanced Format Options"
2. Choose from presets or enter manual format string
3. Examples:
   - `137+140` for 1080p video + AAC audio
   - `bestvideo[height<=720]+bestaudio` for best 720p
   - `best[filesize<100M]` for files under 100MB

## 🔧 Configuration

All settings are automatically saved and restored:
- Quality and format preferences
- Authentication methods
- Proxy configurations
- Download paths
- Subtitle options

## 🐛 Troubleshooting

### Common Issues

1. **"yt-dlp.exe not found"**
   - Make sure `yt-dlp.exe` is in the same directory as `app.py`
   - Download it from [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases)

2. **"Network error: Failed to fetch"**
   - Make sure the Python server is running
   - Check that you're accessing `http://localhost:5000`
   - Verify no firewall is blocking the connection

3. **Subtitle Download Failures**
   - The app automatically retries failed subtitle downloads
   - If subtitles continue to fail, the video will download without them
   - Try using authentication for better success rates

4. **Python not found**
   - Ensure Python is installed and added to PATH
   - Check "Add Python to PATH" during Python installation

### Logs and Debugging

- Check the console output in the terminal where you ran `python app.py`
- The web interface shows real-time download logs
- Look for error messages in the console output section

## 📚 Dependencies

### Python Libraries
- **Flask**: Web framework for the backend API
- **Flask-CORS**: Handles cross-origin requests between frontend and backend

### External Tools
- **yt-dlp**: Command-line YouTube downloader [GitHub](https://github.com/yt-dlp/yt-dlp)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and personal use only. Please respect the terms of service of YouTube and copyright laws. The authors are not responsible for any misuse of this software.

## 🔗 Useful Links

- [yt-dlp GitHub Repository](https://github.com/yt-dlp/yt-dlp)
- [yt-dlp Documentation](https://github.com/yt-dlp/yt-dlp#readme)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Python Official Website](https://www.python.org/)

## 📞 Support

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Search existing issues on GitHub
3. Create a new issue with detailed information about your problem

---

**Made with ❤️ using Python, Flask, and yt-dlp**
